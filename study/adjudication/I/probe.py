"""Blind adjudication probes for task I (tasktrack).

Run as `python3 probe.py` with the implementation's root as the current directory.
Prints one JSON object mapping each defect id (see defects.json) to "DEFECT", "OK" or "N/A".
Only the public surface fixed by the specification is used.
"""
import contextlib
import doctest
import glob
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import traceback

ROOT = os.getcwd()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TMP = tempfile.mkdtemp(prefix="tt_probe_")
ENV = dict(os.environ)
ENV["PYTHONPATH"] = ROOT + (os.pathsep + ENV["PYTHONPATH"] if ENV.get("PYTHONPATH") else "")
ENV["PYTHONIOENCODING"] = "utf-8"
ENV.pop("PYTHONWARNINGS", None)

RESULTS = {}
ERRORS = {}


class NA(Exception):
    """The probe cannot be decided for this implementation."""


def probe(pid):
    def deco(fn):
        def run():
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    r = fn()
                RESULTS[pid] = "DEFECT" if r else "OK"
            except NA as e:
                RESULTS[pid] = "N/A"
                ERRORS[pid] = "N/A: %s" % e
            except BaseException as e:  # noqa: BLE001 - one probe must never stop the others
                RESULTS[pid] = "N/A"
                ERRORS[pid] = "probe error: %r" % (e,)
        run.pid = pid
        PROBES.append(run)
        return fn
    return deco


PROBES = []
_counter = [0]


def fresh(name="f"):
    _counter[0] += 1
    d = os.path.join(TMP, "%s%d" % (name, _counter[0]))
    os.mkdir(d)
    return d


def cli(store, *args, input_bytes=None, timeout=120):
    cmd = [sys.executable, "-m", "tasktrack", "--file", store] + list(args)
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, input=input_bytes,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def pyrun(code, timeout=120):
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=ENV,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def task(**kw):
    from tasktrack.model import normalize
    base = {"id": 1, "title": "Buy", "created": "2026-01-01"}
    base.update(kw)
    return normalize(base)


def md_rejects(line):
    from tasktrack import fmt_md
    from tasktrack.model import TaskError
    try:
        fmt_md.loads(line + "\n")
    except TaskError:
        return True
    return False


def bad_cli(rc, err):
    """True when the CLI did not end the way the spec demands for an error or success."""
    text = err.decode("utf-8", "replace")
    if "Traceback (most recent call last)" in text:
        return True
    return rc not in (0, 2)


# ---------------------------------------------------------------- formats

@probe("D01")
def d01():
    from tasktrack import fmt_md
    t = [task(title="X", tags=["home"])]
    try:
        return fmt_md.loads(fmt_md.dumps(t)) != t
    except Exception:
        return True


@probe("D02")
def d02():
    from tasktrack import fmt_csv
    from tasktrack.model import TaskError
    try:
        t = [task(title="nul\x00x")]
    except TaskError:
        raise NA("normalize rejects a NUL title")
    try:
        return fmt_csv.loads(fmt_csv.dumps(t)) != t
    except Exception:
        return True


@probe("D05")
def d05():
    return not (md_rejects("- [ ]  Buy !2 ^2026-01-01 (7)")
                and md_rejects("- [ ] Buy  !2 ^2026-01-01 (7)"))


@probe("D06")
def d06():
    return not (md_rejects("- [ ] Buy !02 ^2026-01-01 (7)")
                and md_rejects("- [ ] Buy !2 ^2026-01-01 (007)"))


@probe("D07")
def d07():
    return not (md_rejects("- [ ] Buy #b #a !2 ^2026-01-01 (7)")
                and md_rejects("- [ ] Buy #a #a !2 ^2026-01-01 (7)"))


@probe("D08")
def d08():
    good = "- [ ] Buy !2 ^2026-01-01 (7)"
    from tasktrack import fmt_md
    if len(fmt_md.loads(good + "\n\n")) != 1:
        raise NA("valid line or empty line not handled")
    return not (md_rejects("   \n" + good) and md_rejects("\t\n" + good))


@probe("D20")
def d20():
    from tasktrack import fmt_md
    bad = False
    for ch in ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]:
        t = [task(title="a" + ch + "b")]
        try:
            if fmt_md.loads(fmt_md.dumps(t)) != t:
                bad = True
        except Exception:
            bad = True
    return bad


# ---------------------------------------------------------------- store

@probe("D03")
def d03():
    if os.name != "posix":
        raise NA("posix permissions only")
    from tasktrack.store import Store
    path = os.path.join(fresh(), "s.json")
    with open(path, "w") as f:
        f.write('{"next_id": 1, "tasks": []}')
    os.chmod(path, 0o644)
    Store(path).add("x", today="2026-01-01")
    return stat.S_IMODE(os.stat(path).st_mode) != 0o644


@probe("D25")
def d25():
    if os.name != "posix":
        raise NA("posix permissions only")
    code = textwrap.dedent("""
        import os, stat, sys
        os.umask(0o022)
        from tasktrack.store import Store
        p = %r
        Store(p).add("x", today="2026-01-01")
        print(oct(stat.S_IMODE(os.stat(p).st_mode)))
    """) % os.path.join(fresh(), "new.json")
    rc, out, err = pyrun(code)
    if rc != 0:
        raise NA("store add failed: " + err[-200:])
    return out.strip() != "0o644"


@probe("D14")
def d14():
    code = textwrap.dedent("""
        import os
        calls = []
        real = os.umask
        def spy(m):
            calls.append(m)
            return real(m)
        os.umask = spy
        from tasktrack.store import Store
        s = Store(%r)
        s.add("x", today="2026-01-01")
        s.update(1, title="y")
        print(len(calls))
    """) % os.path.join(fresh(), "new.json")
    rc, out, err = pyrun(code)
    if rc != 0:
        raise NA("store add failed: " + err[-200:])
    return int(out.strip()) > 0


@probe("D17")
def d17():
    from tasktrack.store import Store
    s = Store(os.path.join(fresh(), "s.json"))
    s.add("a", today="2026-01-01")
    s.add("b", today="2026-01-01")
    try:
        g = s.get(id=1)
        s.remove(id=2)
    except TypeError:
        return True
    return g["id"] != 1 or [t["id"] for t in s.all()] != [1]


@probe("D24")
def d24():
    if os.name != "posix":
        raise NA("symlinks: posix only")
    from tasktrack.store import Store
    d = fresh()
    os.mkdir(os.path.join(d, "real"))
    target = os.path.join(d, "real", "t.json")
    with open(target, "w") as f:
        f.write('{"next_id": 1, "tasks": []}')
    link = os.path.join(d, "link.json")
    os.symlink(target, link)
    Store(link).add("x", today="2026-01-01")
    if not os.path.islink(link):
        return True
    with open(target) as f:
        data = json.load(f)
    return len(data["tasks"]) != 1


# ---------------------------------------------------------------- query

@probe("D19")
def d19():
    from tasktrack.query import parse
    t = task(tags=["x"])
    try:
        a = parse("not " * 150 + "tag:x")(t)
        b = parse("(" * 150 + "tag:x" + ")" * 150)(t)
    except Exception:
        return True
    return not (a and b)


@probe("D21")
def d21():
    from tasktrack.query import parse
    from tasktrack.model import TaskError
    try:
        parse("(tag:a")
    except TaskError as e:
        return str(e).count("at position") > 1
    raise NA("unclosed parenthesis not rejected")


# ---------------------------------------------------------------- report

@probe("D12")
def d12():
    from tasktrack.report import render
    s = {"total": 3, "open": 3, "done": 0, "overdue": 0,
         "by_priority": {1: 0, 2: 0, 3: 3, 4: 0, 5: 0}, "by_tag": {"b": 1, "a": 2}}
    lines = [l for l in render(s).split("\n") if l.startswith("tag ")]
    if lines == ["tag b: 1", "tag a: 2"]:
        return False
    if lines == ["tag a: 2", "tag b: 1"]:
        return True
    raise NA("unexpected tag lines %r" % lines)


# ---------------------------------------------------------------- command line

def new_store_with_task(title="t", due=None):
    store = os.path.join(fresh(), "s.json")
    args = ["add", title, "--today", "2026-01-01"]
    if due:
        args += ["--due", due]
    rc, out, err = cli(store, *args)
    if rc != 0:
        raise NA("cli add failed: %r" % err[-200:])
    return store


@probe("D04")
def d04():
    store = new_store_with_task("seed")
    src = os.path.join(os.path.dirname(store), "in.jsonl")
    rows = [{"created": "2025-12-01", "due": None, "id": i, "priority": 3, "status": st,
             "tags": [], "title": "imp%d" % i} for i, st in ((1, "done"), (2, "open"), (3, "done"))]
    with open(src, "w") as f:
        f.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    code = textwrap.dedent("""
        import os, runpy, sys
        real = os.replace
        n = [0]
        def flaky(a, b, *k, **kw):
            n[0] += 1
            if n[0] == 2:
                raise OSError(28, "No space left on device (probe)")
            return real(a, b, *k, **kw)
        os.replace = flaky
        sys.argv = ["tasktrack", "--file", %r, "import", "jsonl", %r, "--today", "2026-01-02"]
        runpy.run_module("tasktrack", run_name="__main__", alter_sys=True)
    """) % (store, src)
    pyrun(code)
    with open(store) as f:
        data = json.load(f)
    n = len(data["tasks"])
    if n == 4 or n == 1:
        return False
    return True


@probe("D10")
def d10():
    store = new_store_with_task()
    rc1, _, _ = cli(store, "done", "\u0661")
    rc2, _, _ = cli(store, "add", "y", "--priority", "\u0662", "--today", "2026-01-01")
    return rc1 == 0 or rc2 == 0


@probe("D11")
def d11():
    store = new_store_with_task()
    rc, out, err = cli(store, "add", "a", "b\u2028c\x0bd\x1ce", "--today", "2026-01-01")
    if rc != 2:
        raise NA("extra positional argument not rejected (rc=%r)" % rc)
    return len(err.decode("utf-8", "replace").splitlines()) != 1


@probe("D13")
def d13():
    if os.name != "posix":
        raise NA("bytes argv: posix only")
    store = os.path.join(fresh(), "s.json")
    cmd = [os.fsencode(sys.executable), b"-m", b"tasktrack", b"--file", os.fsencode(store),
           b"add", b"bad\xff", b"--today", b"2026-01-01"]
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return False  # rejected at add: fine
    rc, out, err = cli(store, "list")
    return rc != 0


@probe("D16")
def d16():
    store = new_store_with_task(due="2026-01-05")
    rc, out, err = cli(store, "next", "1", "every", "3", "days")
    return not (rc == 0 and out.decode().strip() == "2026-01-08")


@probe("D23")
def d23():
    big = "1" * 5000
    d = fresh()
    store = os.path.join(d, "s.json")
    rc, out, err = cli(store, "add", "t", "--today", "2026-01-01")
    if rc != 0:
        raise NA("cli add failed")
    bad = False
    rc, out, err = cli(store, "list", "--query", "priority=" + big)
    bad |= bad_cli(rc, err)
    mdf = os.path.join(d, "huge.md")
    with open(mdf, "w") as f:
        f.write("- [ ] x !3 ^2026-01-01 (%s)\n" % big)
    rc, out, err = cli(store, "import", "md", mdf, "--today", "2026-01-01")
    bad |= bad_cli(rc, err)
    csvf = os.path.join(d, "huge.csv")
    with open(csvf, "w") as f:
        f.write("id,title,status,priority,tags,due,created\r\n%s,x,open,3,,,2026-01-01\r\n" % big)
    rc, out, err = cli(store, "import", "csv", csvf, "--today", "2026-01-01")
    bad |= bad_cli(rc, err)
    return bad


# ---------------------------------------------------------------- docs and tests

def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def readme_path():
    c = sorted(glob.glob(os.path.join(ROOT, "README*")))
    return c[0] if c else None


@probe("D09")
def d09():
    p = readme_path()
    if not p:
        raise NA("no README")
    lines = read_text(p).splitlines()
    for i, l in enumerate(lines):
        if re.search(r"tasktrack\b.*\breport\b", l) and i + 1 < len(lines):
            if lines[i + 1].strip().startswith("```"):
                return True
    return False


def doc_files():
    files = sorted(glob.glob(os.path.join(ROOT, "docs", "*.md")))
    p = readme_path()
    if p:
        files.append(p)
    return files


def _compiles(src):
    try:
        compile(src, "<doc>", "exec")
        return True
    except SyntaxError:
        return False


@probe("D18")
def d18():
    files = doc_files()
    if not files:
        raise NA("no docs")
    parser = doctest.DocTestParser()
    for path in files:
        text = read_text(path)
        for ex in parser.get_examples(text):
            if not _compiles(ex.source):
                return True
        for m in re.finditer(r"python3?\s+-c\s+'([^']*)'", text):
            if not _compiles(m.group(1)):
                return True
        for m in re.finditer(r"```python[^\n]*\n(.*?)```", text, re.S):
            body = m.group(1)
            if ">>>" in body:
                continue
            if not _compiles(textwrap.dedent(body)):
                return True
    return False


@probe("D22")
def d22():
    p = os.path.join(ROOT, "docs", "query.md")
    if not os.path.exists(p):
        raise NA("no docs/query.md")
    text = re.sub(r"\s+", " ", read_text(p))
    for sent in re.split(r"(?<=[.;])\s", text):
        low = sent.lower()
        if "whitespace" in low and "optional" in low:
            if not any(q in low for q in ("parenthes", "operator", "around", "only", "except", "word")):
                return True
    return False


@probe("D15")
def d15():
    code = ("import unittest, io, contextlib\n"
            "with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):\n"
            "    s = unittest.defaultTestLoader.discover('.')\n"
            "print(s.countTestCases())\n")
    rc, out, err = pyrun(code)
    if rc != 0:
        raise NA("discover failed: " + err[-200:])
    return int(out.strip().splitlines()[-1]) == 0


MODULES = ["__init__", "__main__", "model", "store", "query", "recur",
           "fmt_jsonl", "fmt_csv", "fmt_md", "report"]
DOCS = ["model", "store", "query", "recur", "formats", "report", "cli"]


@probe("D26")
def d26():
    return any(not os.path.isfile(os.path.join(ROOT, "tasktrack", m + ".py")) for m in MODULES)


@probe("D27")
def d27():
    missing = [d for d in DOCS if not os.path.isfile(os.path.join(ROOT, "docs", d + ".md"))]
    return bool(missing) or readme_path() is None


@probe("D28")
def d28():
    t = lambda n: os.path.isfile(os.path.join(ROOT, "tests", "test_%s.py" % n))  # noqa: E731
    need = ["model", "store", "query", "recur", "report"]
    if any(not t(n) for n in need):
        return True
    if not (t("cli") or t("main") or t("__main__")):
        return True
    fmts = all(t(n) for n in ("fmt_jsonl", "fmt_csv", "fmt_md")) or t("formats")
    return not fmts


def main():
    for run in PROBES:
        run()
    shutil.rmtree(TMP, ignore_errors=True)
    if os.environ.get("PROBE_DEBUG"):
        for k in sorted(ERRORS):
            sys.stderr.write("%s %s\n" % (k, ERRORS[k]))
    order = sorted(RESULTS, key=lambda k: int(k[1:]))
    print(json.dumps({k: RESULTS[k] for k in order}))


if __name__ == "__main__":
    main()
