"""Vérifie que app/ ne contient ni appel réseau externe ni import de tools/."""
import ast
from pathlib import Path

APP_DIR = Path(__file__).parent.parent / "app"
FORBIDDEN_HOSTS = {"api.deepseek.com", "api.openai.com", "api.anthropic.com"}


def _py_files():
    return list(APP_DIR.rglob("*.py"))


def test_no_tools_import_in_app():
    for f in _py_files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [n.name for n in getattr(node, "names", [])]
                module = getattr(node, "module", "") or ""
                all_names = [module] + names
                for name in all_names:
                    assert not (name or "").startswith("tools"), (
                        f"{f.name}: import interdit de tools/ ({name!r})"
                    )


def test_no_external_hostnames_in_app():
    for f in _py_files():
        text = f.read_text(encoding="utf-8")
        for host in FORBIDDEN_HOSTS:
            assert host not in text, f"{f.name}: hôte externe interdit ({host!r})"
