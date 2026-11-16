"""Hidden acceptance test for task I (tasktrack). Run with the run repo as cwd."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.getcwd())

from tasktrack.model import TaskError, normalize  # noqa: E402
from tasktrack.store import Store  # noqa: E402
from tasktrack.query import parse  # noqa: E402
from tasktrack.recur import next_due  # noqa: E402
from tasktrack import fmt_csv, fmt_jsonl, fmt_md, report  # noqa: E402


def task(id, title, status="open", priority=3, tags=(), due=None, created="2026-01-01"):
    return {"id": id, "title": title, "status": status, "priority": priority, "tags": list(tags), "due": due,
            "created": created}


T = [
    task(1, "Buy Milk", priority=1, tags=["home"], due="2026-01-10"),
    task(2, "write report", status="done", tags=["work"]),
    task(3, "Call mom", priority=5, tags=["home", "urgent"], due="2026-02-01"),
    task(4, "milk the cow"),
]


class Model(unittest.TestCase):
    def test_defaults_and_strip(self):
        self.assertEqual(normalize({"id": 1, "title": "  A  ", "created": "2026-01-01"}), task(1, "A"))

    def test_tags(self):
        self.assertEqual(normalize(task(1, "A", tags=[" B ", "a", "b"]))["tags"], ["a", "b"])

    def test_new_object(self):
        src = task(1, "A", tags=["x"])
        keep = copy.deepcopy(src)
        out = normalize(src)
        out["tags"].append("y")
        self.assertEqual(src, keep)

    def test_title_length(self):
        normalize(task(1, "x" * 200))
        for bad in ("", "   ", "x" * 201):
            with self.subTest(bad=len(bad)):
                with self.assertRaises(TaskError):
                    normalize(task(1, bad))

    def test_invalid(self):
        bads = [
            dict(task(1, "A"), priority=0), dict(task(1, "A"), priority=6), dict(task(1, "A"), priority=True),
            dict(task(1, "A"), priority="3"), dict(task(1, "A"), status="x"), dict(task(1, "A"), tags=["a b"]),
            dict(task(1, "A"), tags=[""]), dict(task(1, "A"), due="2026-02-30"), dict(task(1, "A"), due="2026-1-5"),
            dict(task(1, "A"), due="20260105"), dict(task(1, "A"), created="2026-13-01"), dict(task(1, "A"), id=0),
            dict(task(1, "A"), id=True), dict(task(1, "A"), extra=1), {"id": 1, "title": "A"},
            {"title": "A", "created": "2026-01-01"},
        ]
        for i, bad in enumerate(bads):
            with self.subTest(i=i):
                with self.assertRaises(TaskError):
                    normalize(bad)

    def test_is_value_error(self):
        self.assertTrue(issubclass(TaskError, ValueError))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "tasks.json")

    def test_add_ids_persist(self):
        s = Store(self.path)
        a = s.add("One", today="2026-01-01")
        b = s.add(" Two ", today="2026-01-02", priority=5, tags=["B", "a"], due="2026-02-01")
        self.assertEqual(a, task(1, "One"))
        self.assertEqual(b, task(2, "Two", priority=5, tags=["a", "b"], due="2026-02-01", created="2026-01-02"))
        s.remove(2)
        c = s.add("Three", today="2026-01-03")
        self.assertEqual(c["id"], 3)
        again = Store(self.path)
        self.assertEqual([t["id"] for t in again.all()], [1, 3])
        data = json.load(open(self.path))
        self.assertEqual(data["next_id"], 4)
        self.assertEqual(len(data["tasks"]), 2)
        self.assertEqual(os.listdir(self.dir), ["tasks.json"])

    def test_missing_file_is_empty(self):
        self.assertEqual(Store(self.path).all(), [])

    def test_update(self):
        s = Store(self.path)
        s.add("One", today="2026-01-01")
        out = s.update(1, status="done", tags=["B"], title=" New ")
        self.assertEqual(out, task(1, "New", status="done", tags=["b"]))
        self.assertEqual(Store(self.path).get(1), out)
        for bad in ({"created": "2026-02-02"}, {"priority": 9}, {"nope": 1}):
            with self.subTest(bad=bad):
                with self.assertRaises(TaskError):
                    s.update(1, **bad)
        self.assertEqual(s.get(1), out)

    def test_unknown_id(self):
        s = Store(self.path)
        for call in (lambda: s.get(1), lambda: s.remove(1), lambda: s.update(1, title="x")):
            with self.assertRaises(TaskError):
                call()

    def test_copies(self):
        s = Store(self.path)
        s.add("One", today="2026-01-01", tags=["a"])
        got = s.get(1)
        got["title"] = "changed"
        got["tags"].append("zz")
        s.all()[0]["title"] = "changed"
        self.assertEqual(s.get(1), task(1, "One", tags=["a"]))

    def test_invalid_add_changes_nothing(self):
        s = Store(self.path)
        with self.assertRaises(TaskError):
            s.add("", today="2026-01-01")
        self.assertEqual(s.add("ok", today="2026-01-01")["id"], 1)

    def test_corrupt(self):
        for raw in ("{not json", "[1, 2]", '{"next_id": "x", "tasks": []}'):
            with self.subTest(raw=raw):
                with open(self.path, "w") as f:
                    f.write(raw)
                with self.assertRaises(TaskError):
                    Store(self.path).all()


class Query(unittest.TestCase):
    def ids(self, q):
        pred = parse(q)
        return [t["id"] for t in T if pred(t)]

    def test_matches(self):
        cases = {
            "": [1, 2, 3, 4], "   ": [1, 2, 3, 4], "status:open": [1, 3, 4], "tag:home": [1, 3], "due:none": [2, 4],
            "priority>=3": [2, 3, 4], "priority != 3": [1, 3], "priority=1": [1], "due<2026-01-15": [1],
            "due != 2026-01-10": [3], "due>=2026-01-10": [1, 3], 'title~"MILK"': [1, 4], 'title~"k t"': [4],
            "not status:done and tag:home": [1, 3], "status:done or tag:urgent and priority=5": [2, 3],
            "(status:done or tag:urgent) and priority=5": [3], "not (tag:home or status:done)": [4],
            "not not tag:home": [1, 3], "( status:open )": [1, 3, 4], "tag:home and not tag:urgent": [1],
            "priority<2 or priority>4": [1, 3],
        }
        for q, want in cases.items():
            with self.subTest(q=q):
                self.assertEqual(self.ids(q), want)

    def test_syntax_errors(self):
        for q in ("foo:bar", "priority>x", "due<2026-13-01", "(status:open", 'title~"abc', "status:open and",
                  "status:open tag:home", "and", "status:open)", "priority>", "not"):
            with self.subTest(q=q):
                with self.assertRaises(TaskError):
                    parse(q)


class Recur(unittest.TestCase):
    def test_rules(self):
        cases = [
            ("2026-01-31", "daily", "2026-02-01"), ("2026-12-28", "weekly", "2027-01-04"),
            ("2026-01-31", "monthly", "2026-02-28"), ("2028-01-31", "monthly", "2028-02-29"),
            ("2026-12-15", "monthly", "2027-01-15"), ("2026-03-31", "monthly", "2026-04-30"),
            ("2026-01-25", "every 10 days", "2026-02-04"), ("2026-01-01", "every 1 days", "2026-01-02"),
            ("2026-01-09", "weekdays", "2026-01-12"), ("2026-01-10", "weekdays", "2026-01-12"),
            ("2026-01-12", "weekdays", "2026-01-13"),
        ]
        for due, rule, want in cases:
            with self.subTest(due=due, rule=rule):
                self.assertEqual(next_due(due, rule), want)

    def test_errors(self):
        for due, rule in (("2026-01-01", "yearly"), ("2026-01-01", "every 0 days"), ("2026-01-01", "every x days"),
                          ("2026-02-30", "daily"), ("2026-01-01", "")):
            with self.subTest(due=due, rule=rule):
                with self.assertRaises(TaskError):
                    next_due(due, rule)


class Formats(unittest.TestCase):
    def test_round_trips(self):
        tricky = T + [task(5, 'He said "hi", twice', tags=["a-1"], due="2026-03-03")]
        for mod in (fmt_jsonl, fmt_csv, fmt_md):
            with self.subTest(mod=mod.__name__):
                self.assertEqual(mod.loads(mod.dumps(copy.deepcopy(tricky))), tricky)
                self.assertEqual(mod.loads(mod.dumps([])), [])

    def test_jsonl(self):
        lines = fmt_jsonl.dumps(T).strip("\n").split("\n")
        self.assertEqual(len(lines), 4)
        for line, t in zip(lines, T):
            obj = json.loads(line)
            self.assertEqual(obj, t)
            self.assertEqual(list(obj), sorted(obj))
        self.assertEqual(fmt_jsonl.loads("\n" + lines[0] + "\n\n" + lines[1] + "\n"), T[:2])
        for bad in ("{oops", json.dumps({"id": 1}), "[]"):
            with self.subTest(bad=bad):
                with self.assertRaises(TaskError):
                    fmt_jsonl.loads(bad)

    def test_csv(self):
        text = fmt_csv.dumps(T)
        rows = text.splitlines()
        self.assertEqual(rows[0], "id,title,status,priority,tags,due,created")
        self.assertEqual(rows[3], "3,Call mom,open,5,home urgent,2026-02-01,2026-01-01")
        self.assertEqual(rows[2], "2,write report,done,3,work,,2026-01-01")
        with self.assertRaises(TaskError):
            fmt_csv.loads("id,title\n1,A\n")
        with self.assertRaises(TaskError):
            fmt_csv.loads("id,title,status,priority,tags,due,created\nx,A,open,3,,,2026-01-01\n")

    def test_md(self):
        t = task(7, "Buy milk", status="done", priority=2, tags=["home", "shop"], due="2026-01-05")
        self.assertEqual(fmt_md.dumps([t]).strip("\n"), "- [x] Buy milk #home #shop !2 @2026-01-05 ^2026-01-01 (7)")
        self.assertEqual(fmt_md.dumps([task(1, "X")]).strip("\n"), "- [ ] X !3 ^2026-01-01 (1)")
        self.assertEqual(fmt_md.loads("\n- [ ] X !3 ^2026-01-01 (1)\n\n"), [task(1, "X")])
        for bad in ("hello", "- [ ] X", "- [?] X !3 ^2026-01-01 (1)", "- [ ] X !9 ^2026-01-01 (1)"):
            with self.subTest(bad=bad):
                with self.assertRaises(TaskError):
                    fmt_md.loads(bad)
        for title in ("a #b", "a !b", "a @b", "a ^b", "a (b"):
            with self.subTest(title=title):
                with self.assertRaises(TaskError):
                    fmt_md.dumps([task(1, title)])


class Report(unittest.TestCase):
    def test_summary(self):
        s = report.summary(T, "2026-01-20")
        self.assertEqual(s, {"total": 4, "open": 3, "done": 1, "overdue": 1,
                             "by_priority": {1: 1, 2: 0, 3: 1, 4: 0, 5: 1}, "by_tag": {"home": 2, "urgent": 1}})
        self.assertEqual(list(s["by_tag"]), ["home", "urgent"])
        self.assertEqual(report.summary(T, "2026-01-10")["overdue"], 0)

    def test_render(self):
        want = "\n".join(["total: 4", "open: 3", "done: 1", "overdue: 1", "priority 1: 1", "priority 2: 0",
                          "priority 3: 1", "priority 4: 0", "priority 5: 1", "tag home: 2", "tag urgent: 1"])
        self.assertEqual(report.render(report.summary(T, "2026-01-20")), want)
        self.assertEqual(report.render(report.summary([], "2026-01-20")).split("\n")[0], "total: 0")


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.file = os.path.join(self.dir, "t.json")

    def run_cli(self, *args):
        r = subprocess.run([sys.executable, "-m", "tasktrack", "--file", self.file, *args], capture_output=True,
                           text=True, cwd=os.getcwd())
        return r.returncode, r.stdout.strip("\n"), r.stderr

    def test_flow(self):
        self.assertEqual(self.run_cli("add", "Buy milk", "--priority", "2", "--tag", "shop", "--tag", "home",
                                      "--due", "2026-01-05", "--today", "2026-01-01")[:2], (0, "1"))
        self.assertEqual(self.run_cli("add", "Plain", "--today", "2026-01-02")[:2], (0, "2"))
        self.assertEqual(self.run_cli("list")[:2], (0, "- [ ] Buy milk #home #shop !2 @2026-01-05 ^2026-01-01 (1)\n"
                                                       "- [ ] Plain !3 ^2026-01-02 (2)"))
        self.assertEqual(self.run_cli("next", "1", "weekly")[:2], (0, "2026-01-12"))
        self.assertEqual(self.run_cli("done", "1")[:2], (0, ""))
        code, out, _ = self.run_cli("list", "--query", "status:done", "--format", "jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"id": 1, "title": "Buy milk", "status": "done", "priority": 2,
                                           "tags": ["home", "shop"], "due": "2026-01-12", "created": "2026-01-01"})
        code, out, _ = self.run_cli("list", "--format", "csv")
        self.assertEqual(out.splitlines()[0], "id,title,status,priority,tags,due,created")
        self.assertEqual(self.run_cli("report", "--today", "2026-02-01")[1].split("\n")[:4],
                         ["total: 2", "open: 1", "done: 1", "overdue: 0"])
        self.assertEqual(self.run_cli("rm", "2")[:2], (0, ""))
        self.assertEqual(self.run_cli("list", "--query", "status:open")[:2], (0, ""))

    def test_import(self):
        src = os.path.join(self.dir, "in.md")
        with open(src, "w") as f:
            f.write("- [x] Old one #a !4 @2026-05-05 ^2025-01-01 (40)\n- [ ] Other !3 ^2025-01-02 (41)\n")
        self.assertEqual(self.run_cli("import", "md", src, "--today", "2026-03-01")[:2], (0, "2"))
        code, out, _ = self.run_cli("list", "--format", "jsonl")
        got = [json.loads(line) for line in out.split("\n")]
        self.assertEqual(got, [
            {"id": 1, "title": "Old one", "status": "done", "priority": 4, "tags": ["a"], "due": "2026-05-05",
             "created": "2026-03-01"},
            {"id": 2, "title": "Other", "status": "open", "priority": 3, "tags": [], "due": None,
             "created": "2026-03-01"}])

    def test_task_errors_one_line(self):
        self.run_cli("add", "No due", "--today", "2026-01-01")
        bad_import = os.path.join(self.dir, "bad.md")
        with open(bad_import, "w") as f:
            f.write("nonsense\n")
        corrupt = os.path.join(self.dir, "corrupt.json")
        with open(corrupt, "w") as f:
            f.write("{nope")
        cases = [("done", "99"), ("rm", "99"), ("next", "1", "weekly"), ("list", "--query", "foo:bar"),
                 ("add", "", "--today", "2026-01-01"), ("add", "X", "--today", "2026-02-30"),
                 ("import", "md", bad_import, "--today", "2026-01-01"),
                 ("import", "md", os.path.join(self.dir, "missing.md"), "--today", "2026-01-01")]
        for args in cases:
            with self.subTest(args=args):
                code, out, err = self.run_cli(*args)
                self.assertEqual(code, 2, out + err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(len(err.strip().splitlines()), 1, err)
        r = subprocess.run([sys.executable, "-m", "tasktrack", "--file", corrupt, "list"], capture_output=True,
                           text=True, cwd=os.getcwd())
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_bad_arguments(self):
        for args in (("add", "X"), ("frobnicate",), ("list", "--format", "xml"), ("done", "abc")):
            with self.subTest(args=args):
                code, out, err = self.run_cli(*args)
                self.assertEqual(code, 2, out + err)
                self.assertNotIn("Traceback", err)


class Docs(unittest.TestCase):
    def test_files(self):
        for name in ("model", "store", "query", "recur", "formats", "report", "cli"):
            self.assertTrue(os.path.getsize(os.path.join("docs", name + ".md")) > 80, name)
        for name in ("model", "store", "query", "recur", "report"):
            self.assertTrue(os.path.isfile(os.path.join("tests", "test_%s.py" % name)), name)
        self.assertTrue(os.path.isfile("README.md"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
