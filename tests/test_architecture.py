"""Module boundaries (3.3): every package of subagent/ is a module with a public API in its __init__.py; modules
import each other only through that API and only downwards; the app reaches the core only through app/services/."""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A module may import modules on a lower layer only (plus the pairs in SIDEWAYS). cli also holds __main__.py.
LAYERS = {
    "kernel": 0,
    "settings": 1,
    "infra": 2, "llm": 2,
    "workspace": 3,
    "memory": 4,
    "ocr": 5, "voice": 5,
    "cast": 6, "translation": 6,
    "bootstrap": 7, "review": 7,
    "output": 8,
    "pipeline": 9,
    "bench": 10,
    "cli": 11,
}
SIDEWAYS = {("cast", "voice")}      # sprite learning trusts the voice match
APP_CORE = "app/services"           # the only app files that may use the core beyond subagent.kernel


def _imports(path: Path) -> list[ast.ImportFrom | ast.Import]:
    """Every import in a file, including the ones inside functions."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


def _module_of(path: Path) -> str:
    first = path.relative_to(ROOT / "subagent").parts[0]
    return "cli" if first == "__main__.py" else first


def _submodules(package: str) -> set[str]:
    return {m.name for m in pkgutil.iter_modules(importlib.import_module(f"subagent.{package}").__path__)}


def _breaches(path: Path, owner: str) -> list[str]:
    """Imports of other subagent modules that skip the package API, use a private name or point upwards."""
    out = []
    where = f"{path.relative_to(ROOT)}"
    for n in _imports(path):
        if isinstance(n, ast.Import):
            out += [f"{where}:{n.lineno} import {a.name}" for a in n.names if a.name.startswith("subagent.")]
            continue
        if not n.module or n.level or not n.module.startswith("subagent."):
            continue
        target = n.module.split(".")[1]
        if target == owner:
            continue
        if n.module != f"subagent.{target}":
            out.append(f"{where}:{n.lineno} from {n.module}: import from the package subagent.{target}")
        public = set(importlib.import_module(f"subagent.{target}").__all__)
        for a in n.names:
            if a.name.startswith("_") or (a.name in _submodules(target) and a.name not in public):
                out.append(f"{where}:{n.lineno} subagent.{target}.{a.name} is not public")
        if not (LAYERS[target] < LAYERS.get(owner, len(LAYERS)) or (owner, target) in SIDEWAYS):
            out.append(f"{where}:{n.lineno} {owner} -> {target} points upwards")
    return out


def test_every_package_is_a_known_module_with_a_public_api():
    packages = {p.name for p in (ROOT / "subagent").iterdir() if (p / "__init__.py").is_file()}
    assert packages == set(LAYERS), "add the new package to LAYERS"
    for name in sorted(packages - {"cli"}):
        package = importlib.import_module(f"subagent.{name}")
        assert package.__all__, name
        for public in package.__all__:       # every exported name resolves (lazy exports included)
            assert getattr(package, public, None) is not None or public in _submodules(name), f"{name}.{public}"


def test_modules_import_each_other_only_through_their_api_and_downwards():
    breaches = [b for f in sorted((ROOT / "subagent").rglob("*.py")) for b in _breaches(f, _module_of(f))]
    assert not breaches, "\n".join(breaches)


def test_the_core_never_imports_the_app_or_qt():
    bad = [f"{f.relative_to(ROOT)}:{n.lineno}" for f in (ROOT / "subagent").rglob("*.py") for n in _imports(f)
           for name in ([a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""])
           if name.split(".")[0] in ("app", "PySide6")]
    assert not bad, bad


def test_the_app_reaches_the_core_only_through_its_services():
    breaches = []
    for f in sorted((ROOT / "app").rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith(APP_CORE):
            breaches += _breaches(f, "app")       # above every module
            continue
        for n in _imports(f):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            breaches += [f"{rel}:{n.lineno} {name}: use app.services" for name in names
                         if name.startswith("subagent") and name != "subagent.kernel"]
    assert not breaches, "\n".join(breaches)

