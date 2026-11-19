"""SEUL module de l'espace de travail autorisé à toucher le disque (un test d'inventaire le garantit).

Menaces traitées : `..`, chemin absolu, octet nul, lien symbolique (dernier élément OU répertoire intermédiaire),
échange d'un lien symbolique entre la validation et la lecture (TOCTOU), fichier spécial (FIFO, périphérique),
copie altérée sur le disque (SHA-256 recalculé à la lecture).
"""
from __future__ import annotations

import errno
import hashlib
import os
import secrets
import stat
from pathlib import Path

MAX_REL_LEN = 1024
MAX_COMPONENT = 255
MAX_ENTRIES = 5000
MAX_DEPTH = 8
_CHUNK = 1024 * 1024


class PathRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IntegrityError(Exception):
    """La copie figée ne correspond plus à son empreinte enregistrée."""


class TooLarge(Exception):
    pass


class QuotaExceeded(Exception):
    pass


_FORBIDDEN_ROOTS = {"/", "/proc", "/sys", "/dev", "/etc", "/boot", "/root", "/run", "/var", "/usr", "/bin", "/sbin", "/lib"}


# ── configuration (opérateur seulement : jamais depuis l'API) ────────────────────────────────────────────────────

def allowed_roots() -> list[Path]:
    """`WORKSPACE_ALLOWED_ROOTS` (séparateur de chemins du système). Liste vide = aucune source possible."""
    raw = os.environ.get("WORKSPACE_ALLOWED_ROOTS", "")
    roots = []
    for part in raw.split(os.pathsep):
        part = part.strip()
        if part and "\x00" not in part and os.path.isabs(part):
            real = os.path.realpath(part)
            if real in _FORBIDDEN_ROOTS:        # racine du système : jamais une racine d'espace de travail
                continue
            roots.append(Path(real))
    return roots


def storage_dir() -> Path:
    return Path(os.environ.get("WORKSPACE_DIR") or Path(__file__).resolve().parents[2] / "data" / "workspace")


def max_file_bytes() -> int:
    try:
        return max(1, int(os.environ.get("WORKSPACE_MAX_FILE_MB", "100"))) * 1024 * 1024
    except ValueError:
        return 100 * 1024 * 1024


def _under(path: str | Path, root: Path) -> bool:
    p = os.path.realpath(path)
    r = str(root)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


# ── validation ───────────────────────────────────────────────────────────────────────────────────────────────────

def validate_root(root: str) -> str:
    """Racine d'une source : absolue, réelle, sous une racine autorisée par l'opérateur. Renvoie le chemin réel."""
    if not isinstance(root, str) or not root or "\x00" in root or not os.path.isabs(root):
        raise PathRefused("root_invalid", "La racine doit être un chemin absolu valide.")
    allowed = allowed_roots()
    if not allowed:
        raise PathRefused("no_allowed_roots", "Aucune racine autorisée : l'opérateur doit définir WORKSPACE_ALLOWED_ROOTS.")
    real = os.path.realpath(root)
    if not any(_under(real, a) for a in allowed):
        raise PathRefused("root_not_allowed", "Cette racine n'est pas sous une racine autorisée par l'opérateur.")
    store = os.path.realpath(storage_dir())
    if _under(store, Path(real)) or _under(real, Path(store)):
        raise PathRefused("root_overlaps_storage", "La racine ne peut pas contenir le stockage des copies (ni l'inverse).")
    if not os.path.isdir(real):
        raise PathRefused("root_not_directory", "La racine n'est pas un répertoire.")
    return real


def validate_rel(rel: str) -> str:
    """Chemin relatif POSIX propre. Refuse absolu, `..`, `.`, octet nul, antislash, composant trop long."""
    if not isinstance(rel, str) or not rel or len(rel) > MAX_REL_LEN:
        raise PathRefused("path_invalid", "Chemin vide ou trop long.")
    if "\x00" in rel or "\\" in rel:
        raise PathRefused("path_invalid", "Caractère interdit dans le chemin.")
    if rel.startswith("/") or os.path.isabs(rel):
        raise PathRefused("path_absolute", "Chemin absolu refusé : donnez un chemin relatif à la racine.")
    parts = tuple(rel.split("/"))       # pas de normalisation silencieuse : « ./a », « a//b », « a/ » sont refusés
    if not parts or any(p in ("", ".", "..") for p in parts) or any(len(p) > MAX_COMPONENT for p in parts) or len(parts) > MAX_DEPTH + 1:
        raise PathRefused("path_traversal", "Chemin refusé (« .. », composant vide ou trop long).")
    return "/".join(parts)


def _open_under(root: str, rel: str) -> int:
    """Ouvre en lecture seule SANS suivre de lien symbolique final, puis contrôle le chemin réel du descripteur.

    Le contrôle porte sur le descripteur ouvert (pas sur un chemin re-résolu) : un échange de lien entre la validation
    et l'ouverture est donc détecté (O_NOFOLLOW sur le dernier élément ; chemin réel du descripteur pour les
    répertoires intermédiaires)."""
    rel = validate_rel(rel)
    full = os.path.join(root, *rel.split("/"))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOCTTY", 0)
    try:
        fd = os.open(full, flags)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.EMLINK):
            raise PathRefused("symlink_refused", "Lien symbolique refusé.") from None
        if e.errno in (errno.ENOENT, errno.ENOTDIR):
            raise PathRefused("not_found", "Fichier introuvable.") from None
        raise PathRefused("open_failed", "Ouverture impossible.") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise PathRefused("not_regular", "Seuls les fichiers ordinaires sont lisibles.")
        if st.st_nlink > 1:
            raise PathRefused("hardlink_refused", "Fichier à liens multiples (lien dur) refusé.")
        if not os.path.isdir("/proc/self/fd"):      # sans /proc, le contrôle du descripteur est impossible : échec fermé
            raise PathRefused("no_proc", "Contrôle du chemin impossible sur ce système : refusé.")
        real = os.path.realpath(f"/proc/self/fd/{fd}")
        if not _under(real, Path(os.path.realpath(root))):
            raise PathRefused("outside_root", "Le fichier est hors de la racine autorisée.")
        return fd
    except BaseException:
        os.close(fd)
        raise


# ── lecture de la source, copie figée ────────────────────────────────────────────────────────────────────────────

def list_source(root: str) -> list[dict]:
    """Fichiers ordinaires sous la racine (liens symboliques ignorés, jamais suivis). Plafonné."""
    out: list[dict] = []
    base = os.path.realpath(root)
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        depth = dirpath[len(base):].count(os.sep)
        dirnames[:] = sorted(d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))) if depth < MAX_DEPTH else []
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode) or len(fn) > MAX_COMPONENT:
                continue
            try:
                fn.encode("utf-8")
            except UnicodeEncodeError:      # nom non UTF-8 : ni affichable ni journalisable
                continue
            out.append({"path": os.path.relpath(p, base).replace(os.sep, "/"), "size": st.st_size})
            if len(out) >= MAX_ENTRIES:
                return out
    return out


def copy_from_source(root: str, rel: str, source_id: int) -> tuple[str, int]:
    """Copie figée : lit en flux (plafond de taille), calcule le SHA-256, écrit `<source_id>/<sha256>` (0600).

    Retourne (sha256, taille). Ne remplace jamais une copie existante (adressage par contenu)."""
    cap = max_file_bytes()
    fd = _open_under(root, rel)
    d = storage_dir() / str(int(source_id))
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = d / f".tmp-{secrets.token_hex(8)}"
    h, size = hashlib.sha256(), 0
    try:
        with os.fdopen(fd, "rb", closefd=True) as src, os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as dst:
            while chunk := src.read(_CHUNK):
                size += len(chunk)
                if size > cap:
                    raise TooLarge(f"Fichier plus gros que {cap // (1024 * 1024)} Mo.")
                h.update(chunk)
                dst.write(chunk)
        sha = h.hexdigest()
        final = d / sha
        if not final.exists() and _total_bytes() > quota_bytes():      # le fichier temporaire est déjà compté
            raise QuotaExceeded("Quota de stockage de l'espace de travail atteint.")
        os.replace(tmp, final)      # remplace aussi une copie existante altérée (même contenu, écriture atomique)
        return sha, size
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def quota_bytes() -> int:
    try:
        return max(1, int(os.environ.get("WORKSPACE_MAX_TOTAL_MB", "5000"))) * 1024 * 1024
    except ValueError:
        return 5000 * 1024 * 1024


def _total_bytes() -> int:
    total = 0
    for dp, _, fns in os.walk(storage_dir()):
        for fn in fns:
            try:
                total += os.lstat(os.path.join(dp, fn)).st_size
            except OSError:
                pass
    return total


def _copy_path(source_id: int, sha256: str) -> Path:
    if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise PathRefused("sha_invalid", "Empreinte invalide.")
    return storage_dir() / str(int(source_id)) / sha256


def read_copy(source_id: int, sha256: str) -> bytes:
    """Contenu de la copie figée, SHA-256 recalculé : `IntegrityError` en cas d'écart (jamais de contenu altéré servi)."""
    p = _copy_path(source_id, sha256)
    cap = max_file_bytes()
    try:
        with open(p, "rb") as f:
            data = f.read(cap + 1)
    except FileNotFoundError:
        raise IntegrityError("copie absente") from None
    if len(data) > cap:
        raise IntegrityError("copie trop grande")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise IntegrityError("empreinte différente")
    return data


def delete_source_copies(source_id: int) -> None:   # réservé aux tests et à une future purge administrée
    d = storage_dir() / str(int(source_id))
    if d.is_dir():
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
