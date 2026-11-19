"""Validation et conservation des fichiers importés (P-074). Un fichier de tiers est hostile jusqu'à preuve du contraire.

Contrôles (tous échouent par un refus explicite avec un code, jamais par une correction silencieuse) :
- extension autorisée : .csv et .xlsx seulement (.xlsm, .xls, exécutables, archives : refusés) ;
- type RÉEL vérifié sur le contenu (signatures d'exécutables et de documents refusées même sous extension .csv) ;
- taille bornée ; fichier vide refusé ;
- XLSX = archive ZIP : nombre de membres, taille décompressée totale et ratio de compression bornés (bombe ZIP),
  chemins suspects, macros (vbaProject.bin), liens externes et objets incorporés refusés. L'archive n'est jamais extraite sur disque.
- nom d'affichage assaini (séparateurs de chemin, caractères de contrôle et de direction bidi retirés) ;
  le fichier est conservé sous le nom de son SHA-256 : le nom d'origine n'entre jamais dans un chemin.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = int(os.environ.get("SOVEREIGN_AUDIT_MAX_MB", "20")) * 1024 * 1024
MAX_ZIP_MEMBERS = 200
MAX_UNCOMPRESSED = 50 * 1024 * 1024
MAX_MEMBER_RATIO = 100
ALLOWED = {".csv": "csv", ".xlsx": "xlsx"}
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "audit_docs"
_SIGNATURES = {            # signatures de fichiers qui ne doivent jamais passer pour un CSV
    b"MZ": "exécutable Windows", b"\x7fELF": "exécutable Linux", b"#!": "script", b"%PDF": "PDF",
    b"\xca\xfe\xba\xbe": "binaire Java/Mach-O", b"\xd0\xcf\x11\xe0": "document OLE (Office ancien)",
    b"Rar!": "archive RAR", b"7z\xbc\xaf": "archive 7z", b"\x1f\x8b": "archive gzip", b"GIF8": "image", b"\x89PNG": "image",
}
_HASH_RE = re.compile(r"[0-9a-f]{64}")


class FileRefused(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedFile:
    kind: str            # "csv" | "xlsx"
    sha256: str
    display_name: str
    size: int


def safe_display_name(name: str | None) -> str:
    """Nom pour l'affichage seulement : sans chemin, sans caractères de contrôle ni de direction (Cc, Cf)."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = "".join(ch for ch in base if unicodedata.category(ch) not in ("Cc", "Cf", "Cs", "Co", "Cn"))
    base = re.sub(r"\s+", " ", base).strip().lstrip(".")
    return base[:120] or "document"


def _check_zip(data: bytes) -> None:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise FileRefused("not_a_zip", "Fichier XLSX invalide (archive illisible).")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise FileRefused("zip_too_many_members", "Archive XLSX anormale (trop de fichiers internes).")
            total = 0
            names = set()
            for i in infos:
                n = i.filename
                if n.startswith("/") or ".." in n.split("/") or "\\" in n or "\x00" in n:
                    raise FileRefused("zip_unsafe_path", "Archive XLSX refusée (chemin interne suspect).")
                total += i.file_size
                if total > MAX_UNCOMPRESSED:
                    raise FileRefused("zip_bomb", "Archive XLSX refusée (taille décompressée excessive).")
                if i.file_size > 100 * 1024 and i.file_size / max(i.compress_size, 1) > MAX_MEMBER_RATIO:
                    raise FileRefused("zip_bomb", "Archive XLSX refusée (taux de compression anormal).")
                names.add(n.lower())
            if "[content_types].xml" not in names or "xl/workbook.xml" not in names:
                raise FileRefused("not_an_xlsx", "Ce n'est pas un classeur XLSX (structure absente).")
            if any(n.endswith("vbaproject.bin") for n in names):
                raise FileRefused("macros_refused", "Classeur avec macros refusé (VBA).")
            if any(n.startswith("xl/externallinks/") for n in names):
                raise FileRefused("external_links_refused", "Classeur avec liens vers d'autres fichiers refusé.")
            if any(n.startswith(("xl/embeddings/", "xl/activex/")) for n in names):
                raise FileRefused("embedded_objects_refused", "Classeur avec objets incorporés refusé.")
    except zipfile.BadZipFile:
        raise FileRefused("not_a_zip", "Fichier XLSX invalide (archive corrompue).") from None


def validate_upload(filename: str | None, data: bytes) -> ValidatedFile:
    display = safe_display_name(filename)
    ext = Path(display).suffix.lower()
    if ext not in ALLOWED:
        raise FileRefused("unsupported_type", "Format refusé : seuls .csv et .xlsx sont acceptés (ni .xls, ni macros, ni archives).")
    if not data:
        raise FileRefused("empty_file", "Fichier vide.")
    if len(data) > MAX_BYTES:
        raise FileRefused("too_large", f"Fichier trop volumineux (limite {MAX_BYTES // 1024 // 1024} Mo).")
    kind = ALLOWED[ext]
    if kind == "csv":
        for sig, label in _SIGNATURES.items():
            if data.startswith(sig):
                raise FileRefused("content_mismatch", f"Le contenu est un {label}, pas un CSV.")
        if data.startswith(b"PK\x03\x04"):
            raise FileRefused("content_mismatch", "Le contenu est une archive, pas un CSV.")
        if b"\x00" in data[:65536]:
            raise FileRefused("binary_content", "Contenu binaire détecté : ce n'est pas un CSV texte.")
        if data.lstrip(b"\xef\xbb\xbf \t\r\n")[:1] == b"<":
            raise FileRefused("content_mismatch", "Contenu HTML ou XML détecté : ce n'est pas un CSV.")
    else:
        if not data.startswith(b"PK\x03\x04"):
            raise FileRefused("content_mismatch", "Fichier XLSX invalide (signature ZIP absente).")
        _check_zip(data)
    return ValidatedFile(kind=kind, sha256=hashlib.sha256(data).hexdigest(), display_name=display, size=len(data))


# ── conservation de l'original ───────────────────────────────────────────────

def docs_dir() -> Path:
    return Path(os.environ.get("SOVEREIGN_AUDIT_DOCS_DIR") or DEFAULT_DIR)


def original_path(sha256: str, kind: str) -> Path:
    if not _HASH_RE.fullmatch(sha256) or kind not in ("csv", "xlsx"):
        raise ValueError("empreinte ou type invalide")
    d = docs_dir().resolve()
    p = (d / f"{sha256}.{kind}").resolve()
    if p.parent != d:                      # garde de traversée : le chemin reste dans le dossier des originaux
        raise ValueError("chemin hors du dossier des originaux")
    return p


def store_original(vf: ValidatedFile, data: bytes) -> Path:
    """Écrit l'original sous son SHA-256, en lecture seule. Ne l'écrase JAMAIS : si présent, on vérifie qu'il est identique."""
    p = original_path(vf.sha256, vf.kind)
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if p.exists():
        if hashlib.sha256(p.read_bytes()).hexdigest() != vf.sha256:
            raise FileRefused("stored_original_corrupt", "Un original corrompu existe déjà sous cette empreinte : intervention requise.")
        return p
    tmp = p.with_name(f".{uuid.uuid4().hex}.tmp")      # nom unique : un .tmp périmé ne bloque jamais un dépôt
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        os.chmod(p, 0o400)
    finally:
        tmp.unlink(missing_ok=True)
    return p


def read_original(sha256: str, kind: str) -> bytes | None:
    try:
        p = original_path(sha256, kind)
        return p.read_bytes() if p.is_file() else None
    except (ValueError, OSError):
        return None
