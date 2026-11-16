"""Blind defect probes for `dataops` implementations (spec: tasks/H.md).

Run with the implementation's root as the current directory:

    python3 /path/to/probe.py

Prints exactly one JSON object on stdout mapping each defect id (see defects.json)
to "DEFECT", "OK" or "N/A". Diagnostics go to stderr. The implementation is used only
through its public surface: `import dataops`, `dataops.registry.get(name)(rows, **params)`,
`dataops.pipeline.run_pipeline`, `python -m dataops` (subprocess, `sys.executable`), and
the deliverable file paths the spec fixes (`dataops/ops/<name>.py`, `docs/`, `tests/`).
"""

import ast
import contextlib
import json
import math
import os
import subprocess
import sys
import tempfile
import traceback

ROOT = os.getcwd()
sys.path.insert(0, ROOT)

OPS = [
    "select", "drop", "rename", "filter_eq", "filter_range", "sort", "dedupe", "limit",
    "fill", "cast", "concat", "split", "text", "replace", "group_count", "group_sum",
    "group_stats", "top", "round", "join",
]

DEFECT, OK, NA = "DEFECT", "OK", "N/A"

_dataops = None


def dataops():
    global _dataops
    if _dataops is None:
        import dataops as mod  # noqa: F401
        import dataops.registry  # noqa: F401
        import dataops.pipeline  # noqa: F401
        _dataops = mod
    return _dataops


def op(name):
    return dataops().registry.get(name)


def OpError():
    return dataops().registry.OpError


def call(fn, *args, **kwargs):
    """Return ("ok", value) or ("exc", exception)."""
    try:
        return "ok", fn(*args, **kwargs)
    except Exception as exc:  # the implementation's behaviour is what we inspect
        return "exc", exc


def is_operror(res):
    return res[0] == "exc" and isinstance(res[1], OpError())


def returned(res, expected):
    return res[0] == "ok" and res[1] == expected


def has_int_digit_limit():
    return hasattr(sys, "get_int_max_str_digits") and sys.get_int_max_str_digits() > 0


def run_cli(args, files, cwd=None):
    """Write `files` (name -> text) to a temp dir; run `python -m dataops` with `args`
    (names resolved to absolute paths unless cwd is the temp dir)."""
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in files.items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        env = dict(os.environ)
        env["PYTHONPATH"] = ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        if cwd == "tmp":
            argv = list(args)
            run_cwd = tmp
        else:
            argv = [os.path.join(tmp, a) if a in files else a for a in args]
            run_cwd = ROOT
        proc = subprocess.run(
            [sys.executable, "-m", "dataops"] + argv,
            cwd=run_cwd, env=env, capture_output=True, text=True, timeout=120,
        )
        return proc.returncode, proc.stdout, proc.stderr


def cli_crashed(rc, err):
    """Traceback, an exit code other than 0/2, or an exit 2 without exactly one stderr line."""
    if "Traceback (most recent call last)" in err:
        return True
    if rc not in (0, 2):
        return True
    if rc == 2 and len(err.strip().splitlines()) != 1:
        return True
    return False


def strict_json(text):
    def reject(token):
        raise ValueError("non-finite constant " + token)
    return json.loads(text, parse_constant=reject)


# ---------------------------------------------------------------- probes

def p_filter_range_min_gt_max():
    res = call(op("filter_range"), [{"a": 1}, {"a": 3}], field="a", min=5, max=1)
    return OK if returned(res, []) else DEFECT


def p_pipeline_nonstring_op_prefix():
    res = call(dataops().pipeline.run_pipeline, [], [{"op": 5}])
    if is_operror(res) and str(res[1]).startswith("step 1 (5): "):
        return OK
    return DEFECT


def p_field_list_rejects_repeats():
    a = call(op("drop"), [{"a": 1, "b": 2}], fields=["a", "a"])
    b = call(op("concat"), [{"a": "x"}], fields=["a", "a"], into="b", sep="-")
    if returned(a, [{"b": 2}]) and returned(b, [{"a": "x", "b": "x-x"}]):
        return OK
    return DEFECT


def p_field_list_rejects_empty():
    rows = [{"a": "x", "b": "y"}, {"a": "z", "b": "w"}]
    checks = [
        (call(op("select"), [dict(r) for r in rows], fields=[]), [{}, {}]),
        (call(op("drop"), [dict(r) for r in rows], fields=[]), rows),
        (call(op("concat"), [dict(r) for r in rows], fields=[], into="c"),
         [{"a": "x", "b": "y", "c": ""}, {"a": "z", "b": "w", "c": ""}]),
        (call(op("group_count"), [dict(r) for r in rows], by=[]), [{"count": 2}]),
    ]
    return OK if all(returned(res, exp) for res, exp in checks) else DEFECT


def p_rename_empty_mapping():
    res = call(op("rename"), [{"a": 1}], mapping={})
    return OK if returned(res, [{"a": 1}]) else DEFECT


def p_rename_collision_allowed():
    swap = call(op("rename"), [{"a": 1, "b": 2}], mapping={"a": "b", "b": "a"})
    chain = call(op("rename"), [{"a": 1, "b": 2}], mapping={"a": "b", "b": "c"})
    return OK if is_operror(swap) and is_operror(chain) else DEFECT


def p_run_rows_keyword():
    res = call(op("select"), rows=[{"a": 1, "b": 2}], fields=["a"])
    return OK if returned(res, [{"a": 1}]) else DEFECT


def p_cast_int_unicode_digits():
    res = call(op("cast"), [{"a": "\u0663"}, {"a": " \u0661\u0662 "}, {"a": "-\uff11\uff12"}],
               field="a", to="int")
    if res[0] == "ok" and res[1] == [{"a": 3}, {"a": 12}, {"a": -12}] \
            and all(type(r["a"]) is int for r in res[1]):
        return OK
    return DEFECT


def p_cast_int_over_4300_digits():
    if not has_int_digit_limit():
        return NA
    res = call(op("cast"), [{"a": "1" * 5000}], field="a", to="int")
    piped = call(dataops().pipeline.run_pipeline, [{"a": "1" * 5000}],
                 [{"op": "cast", "field": "a", "to": "int"}])
    for r in (res, piped):
        if r[0] == "exc" and not isinstance(r[1], OpError()):
            return DEFECT
    return OK


def p_cli_print_huge_int():
    if not has_int_digit_limit():
        return NA
    big = "9" * 4300
    rows = "[" + ",".join('{"g":1,"v":%s}' % big for _ in range(20)) + "]"
    pipe = json.dumps([{"op": "group_sum", "by": ["g"], "field": "v"}])
    rc, out, err = run_cli(["p.json", "i.json"], {"p.json": pipe, "i.json": rows})
    return DEFECT if cli_crashed(rc, err) else OK


def p_cli_overflow_infinity():
    cases = [
        (json.dumps([{"op": "limit", "n": 10}]), '[{"a": 1e400}]'),
        ('[{"op": "fill", "field": "z", "value": 1e999}]', '[{"k": 1}]'),
    ]
    for pipe, rows in cases:
        rc, out, err = run_cli(["p.json", "i.json"], {"p.json": pipe, "i.json": rows})
        if rc == 0:
            try:
                strict_json(out)
            except ValueError:
                return DEFECT
    return OK


def p_join_nonscalar_cli_crash():
    cases = [
        ([{"op": "join", "other": [{"id": [1]}], "on": "id"}], [{"id": 1}]),
        ([{"op": "join", "other": [{"id": {"a": 1}}], "on": "id"}], [{"id": 1}]),
        ([{"op": "join", "other": [{"k": 1, "v": [1, 2]}], "on": "k"}, {"op": "dedupe"}],
         [{"k": 1}]),
        ([{"op": "join", "other": [{"k": 1, "v": [1, 2]}], "on": "k"},
          {"op": "group_count", "by": ["v"]}], [{"k": 1}]),
        ([{"op": "join", "other": [{"k": 1, "v": [1, 2]}], "on": "k"},
          {"op": "sort", "by": ["v"]}], [{"k": 1}]),
    ]
    for pipe, rows in cases:
        rc, out, err = run_cli(["p.json", "i.json"],
                               {"p.json": json.dumps(pipe), "i.json": json.dumps(rows)})
        if cli_crashed(rc, err):
            return DEFECT
    return OK


def p_join_nonscalar_api():
    a = call(op("join"), [{"k": 1}], other=[{"k": 1, "v": [1, 2]}], on="k")
    b = call(op("join"), [{"k": 1}], other=[{"k": 1, "v": {"x": 1}}], on="k")
    return OK if is_operror(a) and is_operror(b) else DEFECT


def p_join_shared_field_unmatched():
    inner = call(op("join"), [{"k": 1, "b": 1}], other=[{"k": 2, "b": 2}], on="k")
    left = call(op("join"), [{"k": 1, "b": 1}], other=[{"k": 2, "b": 2}], on="k", how="left")
    return OK if is_operror(inner) and is_operror(left) else DEFECT


def p_group_sum_fsum_intermediate():
    rows = [{"g": 1, "v": 1e308}, {"g": 1, "v": 1e308}, {"g": 1, "v": -1e308}]
    res = call(op("group_sum"), rows, by=["g"], field="v")
    if res[0] == "ok" and res[1] == [{"g": 1, "sum": 1e308}] and type(res[1][0]["sum"]) is float:
        return OK
    return DEFECT


def p_group_stats_mean_large_ints():
    rows = [{"g": 1, "v": 10 ** 308}, {"g": 1, "v": 10 ** 308}]
    res = call(op("group_stats"), rows, by=["g"], field="v")
    if res[0] != "ok" or len(res[1]) != 1:
        return DEFECT
    row = res[1][0]
    mean = row.get("mean")
    if isinstance(mean, float) and math.isfinite(mean) and mean == 1e308 and row.get("count") == 2:
        return OK
    return DEFECT


def p_replace_huge_count():
    res = call(op("replace"), [{"s": "aaa"}], field="s", old="a", new="b", count=2 ** 63)
    big = call(op("replace"), [{"s": "aaa"}], field="s", old="a", new="b", count=10 ** 30)
    return OK if returned(res, [{"s": "bbb"}]) and returned(big, [{"s": "bbb"}]) else DEFECT


def p_pipeline_nonstring_param_key():
    res = call(dataops().pipeline.run_pipeline, [{"a": 1}], [{"op": "limit", 1: 2, "n": 1}])
    if is_operror(res) and str(res[1]).startswith("step 1 (limit): "):
        return OK
    return DEFECT


def p_cli_dash_prefixed_paths():
    pipe = json.dumps([{"op": "limit", "n": 5}])
    rows = json.dumps([{"a": 1}])
    for pname in ("--p.json", "-p.json"):
        rc, out, err = run_cli([pname, "i.json"], {pname: pipe, "i.json": rows}, cwd="tmp")
        if rc != 0:
            return DEFECT
        try:
            if strict_json(out) != [{"a": 1}]:
                return DEFECT
        except ValueError:
            return DEFECT
    return OK


def _package_files():
    pkg = os.path.join(ROOT, "dataops")
    out = []
    for dirpath, dirnames, filenames in os.walk(pkg):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in sorted(filenames):
            if f.endswith(".py"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def p_unused_imports():
    files = [f for f in _package_files() if os.path.basename(f) != "__init__.py"]
    if not files:
        return NA
    for path in files:
        tree = _parse(path)
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported[a.asname or a.name.split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for a in node.names:
                    if a.name != "*":
                        imported[a.asname or a.name] = node.lineno
        used = set()
        exported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "__all__" and \
                            isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exported.add(elt.value)
        unused = [n for n in imported if n not in used and n not in exported]
        if unused:
            print("unused imports in %s: %s" % (os.path.relpath(path, ROOT), unused),
                  file=sys.stderr)
            return DEFECT
    return OK


def p_duplicated_helper_code():
    seen = {}
    for path in _package_files():
        tree = _parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.end_lineno - node.lineno + 1 < 5:
                continue
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body = body[1:]
            if not body:
                continue
            key = ast.dump(node.args) + "|" + "".join(ast.dump(s) for s in body)
            other = seen.get(key)
            if other and other[0] != path:
                print("duplicate function: %s:%s and %s:%s" % (
                    os.path.relpath(other[0], ROOT), other[1],
                    os.path.relpath(path, ROOT), node.name), file=sys.stderr)
                return DEFECT
            seen.setdefault(key, (path, node.name))
    return OK


def p_mixed_import_styles():
    ops_dir = os.path.join(ROOT, "dataops", "ops")
    absolute = relative = 0
    for name in OPS:
        path = os.path.join(ops_dir, name + ".py")
        if not os.path.exists(path):
            continue
        tree = _parse(path)
        abs_here = rel_here = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    rel_here = True
                elif node.module and (node.module == "dataops" or node.module.startswith("dataops.")):
                    abs_here = True
            elif isinstance(node, ast.Import):
                if any(a.name == "dataops" or a.name.startswith("dataops.") for a in node.names):
                    abs_here = True
        absolute += abs_here
        relative += rel_here
    return DEFECT if absolute and relative else OK


def p_fill_dead_code():
    path = os.path.realpath(os.path.join(ROOT, "dataops", "ops", "fill.py"))
    if not os.path.exists(path):
        return NA
    tree = _parse(path)
    raise_lines = sorted({n.lineno for n in ast.walk(tree) if isinstance(n, ast.Raise)})
    if not raise_lines:
        return OK
    fill = op("fill")
    hit = set()

    def tracer(frame, event, arg):
        if os.path.realpath(frame.f_code.co_filename) == path:
            if event == "line":
                hit.add(frame.f_lineno)
            return tracer
        return tracer

    class Odd:
        pass

    values = ["x", "", 0, 1, -1, 1.5, 10 ** 400, True, False, None, float("nan"),
              float("inf"), float("-inf"), [1], {"a": 1}, (1,), Odd(), b"x"]
    fields = ["a", "", 1, None, ["a"], True, 1.5, {"a": 1}]
    row_sets = [[], [{}], [{"a": None}], [{"a": 1}], [{"a": None}, {"b": 2}, {"a": "s"}],
                [{"a": [1]}], [1], ["x"], [None], [{1: 2}], None, "x", 5, {"a": 1},
                ({"a": None},), [{"a": float("nan")}]]
    calls = []
    for rows in row_sets:
        for field in fields:
            for value in values:
                calls.append((rows, {"field": field, "value": value}))
        calls.append((rows, {"field": "a"}))
        calls.append((rows, {"value": 1}))
        calls.append((rows, {}))
        calls.append((rows, {"field": "a", "value": 1, "extra": 2}))
        calls.append((rows, {"field": "a", "value": 1, "rows": 2}))
    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        for rows, params in calls:
            try:
                fill(rows, **params)
            except Exception:
                pass
            try:
                dataops().pipeline.run_pipeline(rows, [dict({"op": "fill"}, **params)])
            except Exception:
                pass
    finally:
        sys.settrace(old)
    missed = [ln for ln in raise_lines if ln not in hit]
    if missed:
        print("fill.py raise lines never reached: %s" % missed, file=sys.stderr)
        return DEFECT
    return OK


def p_deliverables_missing():
    missing = []
    for rel in ("dataops/__init__.py", "dataops/registry.py", "dataops/pipeline.py"):
        if not os.path.isfile(os.path.join(ROOT, rel)):
            missing.append(rel)
    if not any(f.lower().startswith("readme") for f in os.listdir(ROOT)):
        missing.append("README")
    for name in OPS:
        for rel in ("dataops/ops/%s.py" % name, "docs/ops/%s.md" % name,
                    "tests/test_%s.py" % name):
            if not os.path.isfile(os.path.join(ROOT, rel)):
                missing.append(rel)
    try:
        names = list(dataops().registry.names())
        if not set(OPS) <= set(names):
            missing.append("registered ops: %s" % sorted(set(OPS) - set(names)))
    except Exception as exc:
        missing.append("registry.names(): %r" % (exc,))
    if missing:
        print("missing deliverables: %s" % missing, file=sys.stderr)
        return DEFECT
    return OK


PROBES = [
    ("D01", p_filter_range_min_gt_max),
    ("D02", p_pipeline_nonstring_op_prefix),
    ("D03", p_field_list_rejects_repeats),
    ("D04", p_field_list_rejects_empty),
    ("D05", p_rename_empty_mapping),
    ("D06", p_rename_collision_allowed),
    ("D07", p_run_rows_keyword),
    ("D08", p_cast_int_unicode_digits),
    ("D09", p_cast_int_over_4300_digits),
    ("D10", p_cli_print_huge_int),
    ("D11", p_cli_overflow_infinity),
    ("D12", p_join_nonscalar_cli_crash),
    ("D13", p_join_nonscalar_api),
    ("D14", p_join_shared_field_unmatched),
    ("D15", p_group_sum_fsum_intermediate),
    ("D16", p_group_stats_mean_large_ints),
    ("D17", p_replace_huge_count),
    ("D18", p_pipeline_nonstring_param_key),
    ("D19", p_cli_dash_prefixed_paths),
    ("D20", p_unused_imports),
    ("D21", p_duplicated_helper_code),
    ("D22", p_mixed_import_styles),
    ("D23", p_fill_dead_code),
    ("D24", p_deliverables_missing),
]


def main():
    results = {}
    for pid, fn in PROBES:
        try:
            with contextlib.redirect_stdout(sys.stderr):
                results[pid] = fn()
        except Exception:
            print("probe %s could not run:" % pid, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results[pid] = NA
    sys.stdout.write(json.dumps(results, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
