"""Rank refactor candidates in this repo from graphify-out/graph.json.

Stdlib only, read-only. Every finding is a lead, not a verdict: the graph is built from static analysis and some of
its edges are inferred, so each candidate must be checked against the code before it goes into a plan.

    python .claude/skills/graph-refactor/scripts/refactor_targets.py [--top N] [--json OUT]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.cwd()
DEP_RELATIONS = {"calls", "references", "uses", "indirect_call", "inherits"}
IMPORT_RELATIONS = {"imports", "imports_from"}
INBOUND_RELATIONS = DEP_RELATIONS | IMPORT_RELATIONS | {"re_exports"}
# Common names that are fine to repeat across files.
GENERIC_NAMES = {"main", "run", "load", "save", "check", "done", "failed", "fill", "show", "render", "label",
                 "describe", "apply", "_norm", "_lines", "_setup", "_line", "__getattr__", "__init__", "fetch"}
QT_HOOKS = {"event", "paintevent", "resizeevent", "showevent", "hideevent", "closeevent", "keypressevent",
            "mousepressevent", "mousemoveevent", "mousereleaseevent", "wheelevent", "dragenterevent",
            "dragmoveevent", "dropevent", "sizehint", "minimumsizehint", "additem", "count", "itemat", "takeat",
            "expandingdirections", "hasheightforwidth", "heightforwidth", "setgeometry", "data", "rowcount",
            "columncount", "headerdata", "flags", "setdata", "changeevent", "eventfilter", "focusinevent",
            "focusoutevent", "contextmenuevent", "leaveevent", "enterevent", "timerevent"}


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def layer_rules() -> tuple[dict[str, int], set[tuple[str, str]]]:
    """LAYERS and SIDEWAYS from tests/test_architecture.py, so the script never disagrees with the guard test."""
    tree = ast.parse((ROOT / "tests" / "test_architecture.py").read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        target = node.targets[0] if isinstance(node, ast.Assign) else None
        if isinstance(target, ast.Name) and target.id in ("LAYERS", "SIDEWAYS"):
            found[target.id] = ast.literal_eval(node.value)
    return found["LAYERS"], set(found["SIDEWAYS"])


def package(path: str) -> str:
    """The module a file belongs to: a subagent package, 'app.services', 'app', 'tests' or ''."""
    parts = Path(path).parts
    if not parts:
        return ""
    if parts[0] == "subagent":
        return "cli" if len(parts) == 2 and parts[1] == "__main__.py" else (parts[1] if len(parts) > 2 else "")
    if parts[0] == "app":
        return "app.services" if len(parts) > 2 and parts[1] == "services" else "app"
    return parts[0] if parts[0] == "tests" else ""


def is_file_node(n: dict) -> bool:
    return n.get("label") == Path(n.get("source_file", "")).name


def line_count(path: str) -> int:
    try:
        return sum(1 for _ in (ROOT / path).open(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def framework_called(path: str) -> set[int]:
    """Def lines of functions a framework calls for us: decorated by anything but @classmethod / @staticmethod
    (Pydantic validators, properties, Qt slots, fixtures)."""
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    plain = {"classmethod", "staticmethod"}
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
            names = {ast.unparse(d).split("(")[0].split(".")[-1] for d in n.decorator_list}
            if names - plain:
                out.add(n.lineno)
    return out


def scc(graph: dict[str, set[str]]) -> list[list[str]]:
    """Strongly connected components with more than one member (iterative Tarjan)."""
    index, low, on, stack, out, counter = {}, {}, set(), [], [], [0]
    for start in graph:
        if start in index:
            continue
        work = [(start, iter(graph.get(start, ())))]
        index[start] = low[start] = counter[0]
        counter[0] += 1
        stack.append(start)
        on.add(start)
        while work:
            v, it = work[-1]
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter[0]
                    counter[0] += 1
                    stack.append(w)
                    on.add(w)
                    work.append((w, iter(graph.get(w, ()))))
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    if len(comp) > 1:
                        out.append(sorted(comp))
    return out


def analyse(graph_path: Path, top: int) -> dict:
    g = json.loads(graph_path.read_text(encoding="utf-8"))
    links = g.get("links") or g.get("edges") or []
    nodes = {n["id"]: n for n in g["nodes"]}
    layers, sideways = layer_rules()

    def src(n_id: str) -> str:
        return nodes.get(n_id, {}).get("source_file", "")

    code = {i: n for i, n in nodes.items() if n.get("file_type") == "code" and src(i).endswith(".py")}
    prod = {i: n for i, n in code.items() if package(src(i)) not in ("tests", "")}

    # Freshness: the graph is only as good as the commit it was built from.
    built = g.get("built_at_commit") or ""
    head = git("rev-parse", "HEAD")
    changed = git("diff", "--name-only", built, "--", "*.py").splitlines() if built and built != head else []
    changed += [p for p in git("diff", "--name-only", "HEAD", "--", "*.py").splitlines() if p not in changed]
    freshness = {"built_at_commit": built, "head": head, "changed_py_since_build": changed}

    inbound: dict[str, list[dict]] = defaultdict(list)
    outbound: dict[str, list[dict]] = defaultdict(list)
    for e in links:
        inbound[e["target"]].append(e)
        outbound[e["source"]].append(e)

    # 1a. App files that drive the core: the core names a view reaches (through app/services/ re-exports, which
    # the graph resolves to the core symbol). Many names from many modules means core logic living in the UI.
    # Import rules themselves are tests/test_architecture.py's job.
    ui = defaultdict(lambda: {"modules": Counter(), "names": set()})
    # 1b. Coupling between core modules: dependency edges per (from, to) module pair.
    coupling = Counter()
    upward = defaultdict(list)
    for e in links:
        if e["relation"] not in DEP_RELATIONS or e["source"] not in code or e["target"] not in code:
            continue
        sp, tp = package(src(e["source"])), package(src(e["target"]))
        if sp == tp or tp in ("tests", "app", "app.services", ""):
            continue
        if sp in ("app", "app.services") and tp != "kernel":
            u = ui[src(e["source"])]
            u["modules"][tp] += 1
            u["names"].add(nodes[e["target"]]["label"])
        elif sp in layers and tp in layers:
            if tp not in ("kernel", "settings"):     # every module leans on the foundation; that is by design
                coupling[(sp, tp)] += 1
            if not (layers[tp] < layers[sp] or (sp, tp) in sideways) and e.get("confidence") == "EXTRACTED":
                upward[(sp, tp)].append(f'{nodes[e["source"]]["label"]} -> {nodes[e["target"]]["label"]} '
                                        f'({e.get("source_file")}:{e.get("source_location")})')
    ui_out = sorted(({"file": f, "core_modules": len(v["modules"]), "core_names": len(v["names"]),
                      "by_module": dict(v["modules"].most_common())} for f, v in ui.items()
                     if package(f) == "app"), key=lambda x: (-x["core_modules"], -x["core_names"]))
    coupling_out = [{"from": a, "to": b, "edges": n} for (a, b), n in coupling.most_common()]
    upward_out = [{"from": a, "to": b, "examples": v[:3], "edges": len(v)} for (a, b), v in upward.items()]

    # 2. Files that do several jobs: many symbols spread over several communities.
    by_file: dict[str, list[dict]] = defaultdict(list)
    for i, n in prod.items():
        if not is_file_node(n):
            by_file[src(i)].append(n)
    files = []
    for f, syms in by_file.items():
        comms = Counter(s.get("community_name") or s.get("community") for s in syms)
        main_share = comms.most_common(1)[0][1] / len(syms)
        lines = line_count(f)
        files.append({"file": f, "lines": lines, "symbols": len(syms), "communities": len(comms),
                      "main_community_share": round(main_share, 2),
                      "community_split": dict(comms.most_common(4)),
                      "score": round(lines / 100 * (1 - main_share) * len(comms), 1)})
    files.sort(key=lambda x: -x["score"])

    # 3. Large classes (method count) and long functions (distinct callees).
    classes = []
    for i, n in prod.items():
        if n.get("_callable_class"):
            methods = [e for e in outbound[i] if e["relation"] == "method"]
            if len(methods) >= 15:
                classes.append({"class": n["label"], "file": src(i), "line": n.get("source_location"),
                                "methods": len(methods)})
    classes.sort(key=lambda x: -x["methods"])
    callers = []
    for i, n in prod.items():
        if n.get("_callable") and not n.get("_callable_class"):
            callees = {e["target"] for e in outbound[i] if e["relation"] in ("calls", "indirect_call")}
            if len(callees) >= 20:
                callers.append({"function": n["label"], "file": src(i), "line": n.get("source_location"),
                                "distinct_callees": len(callees)})
    callers.sort(key=lambda x: -x["distinct_callees"])

    # 4. Hubs: high fan-in from other files. Not targets by themselves; they set the blast radius of a change.
    hubs = []
    for i, n in prod.items():
        if is_file_node(n):
            continue
        from_files = {src(e["source"]) for e in inbound[i]
                      if e["relation"] in DEP_RELATIONS and src(e["source"]) != src(i)}
        if len(from_files) >= 10:
            hubs.append({"symbol": n["label"], "file": src(i), "used_by_files": len(from_files),
                         "tests_among_them": sum(package(f) == "tests" for f in from_files)})
    hubs.sort(key=lambda x: -x["used_by_files"])

    # 5. Import cycles between project files. Lazy __getattr__ exports and TYPE_CHECKING imports show up here as
    # cycles that never run; check each one in the code.
    file_ids = {i: src(i) for i, n in code.items() if is_file_node(n)}
    imports: dict[str, set[str]] = defaultdict(set)
    for e in links:
        a, b = file_ids.get(e["source"]), file_ids.get(e["target"])
        if e["relation"] in IMPORT_RELATIONS and a and b and package(a) != "tests":
            imports[a].add(b)
    cycles = scc(imports)

    # 6. Symbols nothing points at. Strong false-positive risk (Qt signal slots, getattr, CLI tables, strings).
    words = Counter()
    for py in list(ROOT.glob("subagent/**/*.py")) + list(ROOT.glob("app/**/*.py")) + list(ROOT.glob("tests/**/*.py")):
        words.update(re.findall(r"\w+", py.read_text(encoding="utf-8", errors="replace")))
    decorated: dict[str, set[int]] = {}
    unused = []
    for i, n in prod.items():
        if not n.get("_callable") or n.get("_callable_class") or is_file_node(n):
            continue
        name = n["label"].strip(".()").lower()
        if name.startswith("__") or name in QT_HOOKS or name.startswith(("test", "cmd_")):
            continue
        bare = n["label"].strip(".()")
        if words[bare] > 1:      # named somewhere else: a Qt connect, getattr, a test, a table of callables
            continue
        line = int(str(n.get("source_location") or "L0").lstrip("L") or 0)
        if line in decorated.setdefault(src(i), framework_called(src(i))):
            continue
        if not any(e["relation"] in INBOUND_RELATIONS and e["source"] != i for e in inbound[i]):
            unused.append({"symbol": n["label"], "file": src(i), "line": n.get("source_location")})
    unused.sort(key=lambda x: (x["file"], x["symbol"]))

    # 7. Possible duplicates: the same function name defined in several production files.
    names: dict[str, list[str]] = defaultdict(list)
    for i, n in prod.items():
        if n.get("_callable") and not n.get("_callable_class") and not n["label"].startswith("."):
            nm = n["label"].strip("()")
            if nm not in GENERIC_NAMES:
                names[nm].append(f'{src(i)}:{n.get("source_location")}')
    dups = sorted(({"name": k, "defined_in": v} for k, v in names.items() if len({p.split(":")[0] for p in v}) > 1),
                  key=lambda x: -len(x["defined_in"]))

    return {"freshness": freshness, "ui_core": ui_out[:top], "coupling": coupling_out[:top],
            "upward": upward_out, "files": files[:top], "classes": classes[:top],
            "long_functions": callers[:top], "hubs": hubs[:top], "cycles": cycles, "unreferenced": unused,
            "duplicate_names": dups[:top]}


def markdown(r: dict) -> str:
    f = r["freshness"]
    out = ["# Refactor candidates from the graph", ""]
    if f["changed_py_since_build"]:
        out += [f"**Graph is stale:** built at `{f['built_at_commit'][:7]}`, HEAD is `{f['head'][:7]}`; "
                f"{len(f['changed_py_since_build'])} Python file(s) changed since. Run `graphify update .` first.", ""]
    else:
        out += [f"Graph is current (built at `{f['built_at_commit'][:7]}`, no Python changes since).", ""]

    out += ["## 1. App files that drive the core", "",
            "Core names each app file reaches through app/services/. Many modules here means core logic in the UI.",
            "", "| File | Core modules | Core names | By module |", "|---|---|---|---|"]
    out += [f"| `{x['file']}` | {x['core_modules']} | {x['core_names']} | "
            f"{', '.join(f'{k} {v}' for k, v in x['by_module'].items())} |" for x in r["ui_core"]]
    out += ["", "Coupling between core modules (dependency edges, top pairs; kernel and settings left out):", ""]
    out += [f"- {x['from']} -> {x['to']}: {x['edges']}" for x in r["coupling"]]
    if r["upward"]:
        out += ["", "Extracted call or inheritance edges that point up the layers (imports are checked by "
                    "tests/test_architecture.py; these come from elsewhere, e.g. callbacks):", ""]
        for x in r["upward"]:
            out.append(f"- {x['from']} -> {x['to']}: {x['edges']}")
            out += [f"  - {e}" for e in x["examples"]]

    out += ["", "## 2. Files that do several jobs", "", "| File | Lines | Symbols | Communities | Main share | Score |",
            "|---|---|---|---|---|---|"]
    out += [f"| `{x['file']}` | {x['lines']} | {x['symbols']} | {x['communities']} | {x['main_community_share']} "
            f"| {x['score']} |" for x in r["files"]]

    out += ["", "## 3. Large classes and long functions", ""]
    out += [f"- class `{x['class']}` ({x['file']}:{x['line']}): {x['methods']} methods" for x in r["classes"]]
    out += [f"- `{x['function']}` ({x['file']}:{x['line']}): calls {x['distinct_callees']} distinct functions"
            for x in r["long_functions"]]

    out += ["", "## 4. Hubs (blast radius, not targets)", ""]
    out += [f"- `{x['symbol']}` ({x['file']}): used by {x['used_by_files']} files ({x['tests_among_them']} tests)"
            for x in r["hubs"]]

    out += ["", "## 5. Import cycles (check for lazy or TYPE_CHECKING imports)", ""]
    out += [f"- {' -> '.join(c)}" for c in r["cycles"]] or ["- none found"]

    out += ["", f"## 6. Unreferenced symbols ({len(r['unreferenced'])}: no graph edge in, name appears once in the "
                f"repo's Python; grep before trusting)", ""]
    out += [f"- `{x['symbol']}` ({x['file']}:{x['line']})" for x in r["unreferenced"][:40]]
    if len(r["unreferenced"]) > 40:
        out.append(f"- … {len(r['unreferenced']) - 40} more in the JSON output")

    out += ["", "## 7. Same function name in several files", ""]
    out += [f"- `{x['name']}`: {', '.join(x['defined_in'])}" for x in r["duplicate_names"]] or ["- none found"]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graph", type=Path, default=ROOT / "graphify-out" / "graph.json")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", type=Path, help="also write the full result as JSON here")
    a = ap.parse_args()
    if not a.graph.is_file():
        print(f"No graph at {a.graph}. Build it first with /graphify.", file=sys.stderr)
        return 1
    result = analyse(a.graph, a.top)
    if a.json:
        a.json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.stdout.write(markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
