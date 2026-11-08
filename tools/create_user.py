"""Create a web account from the command line (password prompted, never an argument).

    python tools/create_user.py someone@example.org --role editor

Uses the same database as the API (SOVEREIGN_AUTH_DB, default ./auth.db) and the same
e-mail/password rules as POST /auth/users. In Docker: docker compose exec api python tools/create_user.py ...
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import security as sec  # noqa: E402
from app.feedback import record_audit  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("email")
    ap.add_argument("--role", choices=sec.VALID_ROLES, default="viewer")
    args = ap.parse_args(argv)

    if not sys.stdin.isatty():
        # Without a TTY getpass falls back to an echoing prompt: the password would be printed.
        print("Entrée non interactive : relancer avec un terminal (docker exec -it ...).", file=sys.stderr)
        return 1
    try:
        email = sec.validate_email(args.email)
        password = getpass.getpass("Mot de passe : ")
        if password != getpass.getpass("Confirmer : "):
            print("Les mots de passe ne correspondent pas.", file=sys.stderr)
            return 1
        sec.validate_password(password)
        sec.init_auth_db()
        user_id = sec.create_user(email, password, args.role)
    except (ValueError, sec.UserExistsError) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 1
    try:
        record_audit("user_created", {"actor": "cli", "user_id": user_id, "role": args.role})
    except OSError:
        print("Avertissement : journal d'audit non écrit.", file=sys.stderr)
    print(f"Compte créé : id={user_id} email={email} rôle={args.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
