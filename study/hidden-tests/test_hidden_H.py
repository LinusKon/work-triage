"""Hidden acceptance test for task H (dataops). Run with the run repo as cwd."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.getcwd())

import dataops  # noqa: E402,F401
from dataops.registry import OpError, get, names, register  # noqa: E402
from dataops.pipeline import run_pipeline  # noqa: E402

ERR = object()
OPS = ["cast", "concat", "dedupe", "drop", "fill", "filter_eq", "filter_range", "group_count", "group_stats",
       "group_sum", "join", "limit", "rename", "replace", "round", "select", "sort", "split", "text", "top"]

R = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 1, "b": "z"}]

# (op, params, input rows, expected rows or ERR)
CASES = [
    ("select", {"fields": ["b", "a"]}, R, [{"b": "x", "a": 1}, {"b": "y", "a": 2}, {"b": "z", "a": 1}]),
    ("select", {"fields": ["nope"]}, R, ERR),
    ("select", {}, R, ERR),
    ("select", {"fields": ["a"], "extra": 1}, R, ERR),
    ("select", {"fields": "a"}, R, ERR),
    ("drop", {"fields": ["b", "nope"]}, R, [{"a": 1}, {"a": 2}, {"a": 1}]),
    ("rename", {"mapping": {"a": "id"}}, R[:1], [{"id": 1, "b": "x"}]),
    ("rename", {"mapping": {"a": "b"}}, R[:1], ERR),
    ("rename", {"mapping": {"zz": "q"}}, R[:1], ERR),
    ("filter_eq", {"field": "a", "value": 1.0}, R, [{"a": 1, "b": "x"}, {"a": 1, "b": "z"}]),
    ("filter_eq", {"field": "a", "value": True}, [{"a": 1}, {"a": True}, {}], [{"a": True}]),
    ("filter_eq", {"field": "a", "value": 1}, [{"a": True}, {"a": 1}], [{"a": 1}]),
    ("filter_range", {"field": "a", "min": 2}, R + [{"a": None}, {"a": "5"}, {"b": 1}, {"a": True}],
     [{"a": 2, "b": "y"}]),
    ("filter_range", {"field": "a", "min": 1, "max": 1}, R, [{"a": 1, "b": "x"}, {"a": 1, "b": "z"}]),
    ("filter_range", {"field": "a"}, R, ERR),
    ("sort", {"by": ["a"]}, [{"a": 2, "k": 1}, {"a": None, "k": 2}, {"a": 1, "k": 3}, {"a": 2, "k": 4}],
     [{"a": None, "k": 2}, {"a": 1, "k": 3}, {"a": 2, "k": 1}, {"a": 2, "k": 4}]),
    ("sort", {"by": ["a"], "descending": True}, [{"a": 1}, {"a": None}, {"a": 3}], [{"a": 3}, {"a": 1}, {"a": None}]),
    ("sort", {"by": ["a", "b"]}, [{"a": 1, "b": "z"}, {"a": 1, "b": "a"}, {"a": 0, "b": "m"}],
     [{"a": 0, "b": "m"}, {"a": 1, "b": "a"}, {"a": 1, "b": "z"}]),
    ("sort", {"by": ["a"]}, [{"a": 1}, {"a": "x"}], ERR),
    ("sort", {"by": ["a"]}, [{"a": True}, {"a": False}], ERR),
    ("sort", {"by": ["a"]}, [{"a": 1}, {"b": 2}], ERR),
    ("dedupe", {"fields": ["a"]}, R, [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]),
    ("dedupe", {}, [{"a": 1}, {"a": 1.0}, {"a": True}, {"a": 1}], [{"a": 1}, {"a": True}]),
    ("dedupe", {"fields": ["z"]}, [{"a": 1}, {"z": None}, {"z": 2}], [{"a": 1}, {"z": 2}]),
    ("limit", {"n": 1, "offset": 1}, R, [{"a": 2, "b": "y"}]),
    ("limit", {"n": 0}, R, []),
    ("limit", {"n": 10, "offset": 5}, R, []),
    ("limit", {"n": -1}, R, ERR),
    ("limit", {"n": True}, R, ERR),
    ("fill", {"field": "c", "value": 0}, [{"c": None}, {}, {"c": 5}], [{"c": 0}, {"c": 0}, {"c": 5}]),
    ("cast", {"field": "v", "to": "int"}, [{"v": " 12 "}, {"v": 3.0}, {"v": None}, {"v": "-7"}],
     [{"v": 12}, {"v": 3}, {"v": None}, {"v": -7}]),
    ("cast", {"field": "v", "to": "int"}, [{"v": "1.5"}], ERR),
    ("cast", {"field": "v", "to": "int"}, [{"v": 1.5}], ERR),
    ("cast", {"field": "v", "to": "float"}, [{"v": "1e2"}, {"v": 2}], [{"v": 100.0}, {"v": 2.0}]),
    ("cast", {"field": "v", "to": "float"}, [{"v": "nan"}], ERR),
    ("cast", {"field": "v", "to": "float"}, [{"v": "inf"}], ERR),
    ("cast", {"field": "v", "to": "str"}, [{"v": True}, {"v": 1.5}, {"v": 2}, {"v": "s"}],
     [{"v": "true"}, {"v": "1.5"}, {"v": "2"}, {"v": "s"}]),
    ("cast", {"field": "v", "to": "bool"}, [{"v": " YES "}, {"v": "0"}, {"v": False}],
     [{"v": True}, {"v": False}, {"v": False}]),
    ("cast", {"field": "v", "to": "bool"}, [{"v": "maybe"}], ERR),
    ("cast", {"field": "v", "to": "date"}, [{"v": "1"}], ERR),
    ("concat", {"fields": ["b", "c"], "into": "d", "sep": "-"}, [{"b": "x", "c": "y"}], [{"b": "x", "c": "y", "d": "x-y"}]),
    ("concat", {"fields": ["a", "b"], "into": "d"}, R[:1], ERR),
    ("concat", {"fields": ["b"], "into": "a"}, R[:1], ERR),
    ("split", {"field": "s", "sep": ":", "into": ["h", "m"]}, [{"s": "1:2:3"}], [{"s": "1:2:3", "h": "1", "m": "2:3"}]),
    ("split", {"field": "s", "sep": ":", "into": ["h", "m", "x"]}, [{"s": "1:2"}], ERR),
    ("split", {"field": "s", "sep": "", "into": ["h"]}, [{"s": "1"}], ERR),
    ("split", {"field": "s", "sep": ":", "into": ["s", "m"]}, [{"s": "1:2"}], ERR),
    ("text", {"field": "b", "mode": "upper"}, [{"b": "ab c"}, {"b": None}], [{"b": "AB C"}, {"b": None}]),
    ("text", {"field": "b", "mode": "title"}, [{"b": "ab c"}], [{"b": "Ab C"}]),
    ("text", {"field": "b", "mode": "strip"}, [{"b": "  x "}], [{"b": "x"}]),
    ("text", {"field": "a", "mode": "upper"}, R[:1], ERR),
    ("text", {"field": "b", "mode": "swap"}, R[:1], ERR),
    ("replace", {"field": "b", "old": "a", "new": "o", "count": 2}, [{"b": "banana"}, {"b": None}],
     [{"b": "bonona"}, {"b": None}]),
    ("replace", {"field": "b", "old": "a", "new": ""}, [{"b": "banana"}], [{"b": "bnn"}]),
    ("replace", {"field": "b", "old": "", "new": "x"}, [{"b": "a"}], ERR),
    ("replace", {"field": "b", "old": "a", "new": "x", "count": 0}, [{"b": "a"}], ERR),
    ("group_count", {"by": ["a"]}, R, [{"a": 1, "count": 2}, {"a": 2, "count": 1}]),
    ("group_count", {"by": ["a"], "into": "n"}, R[:1], [{"a": 1, "n": 1}]),
    ("group_sum", {"by": ["g"], "field": "v"}, [{"g": "x", "v": 1}, {"g": "y", "v": None}, {"g": "x", "v": 2}, {"g": "y"}],
     [{"g": "x", "sum": 3}, {"g": "y", "sum": 0}]),
    ("group_sum", {"by": ["g"], "field": "v"}, [{"g": 1, "v": 0.1}, {"g": 1, "v": 0.2}, {"g": 1, "v": 0.3}],
     [{"g": 1, "sum": 0.6}]),
    ("group_sum", {"by": ["g"], "field": "v"}, [{"g": 1, "v": 1e308}, {"g": 1, "v": 1e308}], ERR),
    ("group_sum", {"by": ["g"], "field": "v"}, [{"g": 1, "v": "3"}], ERR),
    ("group_sum", {"by": ["g"], "field": "v"}, [{"g": 1, "v": True}], ERR),
    ("group_stats", {"by": ["g"], "field": "v"}, [{"g": 1, "v": 1}, {"g": 1, "v": 4}, {"g": 2, "v": None}],
     [{"g": 1, "sum": 5, "count": 2, "min": 1, "max": 4, "mean": 2.5},
      {"g": 2, "sum": 0, "count": 0, "min": None, "max": None, "mean": None}]),
    ("group_stats", {"by": ["g"], "field": "v"}, [{"g": 1, "v": 1e308}, {"g": 1, "v": 1e308}], ERR),
    ("top", {"n": 2, "by": "v"}, [{"v": 1, "k": "a"}, {"v": 3, "k": "b"}, {"v": 3, "k": "c"}, {"v": None}, {"k": "z"}],
     [{"v": 3, "k": "b"}, {"v": 3, "k": "c"}]),
    ("top", {"n": 1, "by": "v", "descending": False}, [{"v": 2}, {"v": 1}], [{"v": 1}]),
    ("top", {"n": 1, "by": "v"}, [{"v": "9"}], ERR),
    ("round", {"field": "v", "digits": 2}, [{"v": 2.675}, {"v": None}, {"v": -2.675}], [{"v": 2.68}, {"v": None}, {"v": -2.68}]),
    ("round", {"field": "v"}, [{"v": 2.5}, {"v": 3.5}, {"v": -0.5}, {"v": 7}], [{"v": 3}, {"v": 4}, {"v": -1}, {"v": 7}]),
    ("round", {"field": "v", "digits": -1}, [{"v": 1}], ERR),
    ("round", {"field": "v"}, [{"v": "1"}], ERR),
    ("join", {"other": [{"a": 1, "n": "one"}, {"a": 1, "n": "uno"}, {"a": 3, "n": "three"}], "on": "a"}, R,
     [{"a": 1, "b": "x", "n": "one"}, {"a": 1, "b": "x", "n": "uno"}, {"a": 1, "b": "z", "n": "one"},
      {"a": 1, "b": "z", "n": "uno"}]),
    ("join", {"other": [{"a": 2, "n": "two"}], "on": "a", "how": "left"}, R,
     [{"a": 1, "b": "x"}, {"a": 2, "b": "y", "n": "two"}, {"a": 1, "b": "z"}]),
    ("join", {"other": [{"a": 1, "b": "clash"}], "on": "a"}, R, ERR),
    ("join", {"other": [{"n": 1}], "on": "a"}, R, ERR),
    ("join", {"other": [{"a": 1}], "on": "a", "how": "outer"}, R, ERR),
]


class Operations(unittest.TestCase):
    def test_cases(self):
        for i, (op, params, rows, want) in enumerate(CASES):
            with self.subTest(i=i, op=op, params=params):
                given = copy.deepcopy(rows)
                p = copy.deepcopy(params)
                if want is ERR:
                    with self.assertRaises(OpError):
                        get(op)(given, **p)
                else:
                    got = get(op)(given, **p)
                    self.assertEqual(got, want)
                    self.assertEqual([list(r) for r in got], [list(r) for r in want], "field order")
                    self.assertEqual([[type(v) for v in r.values()] for r in got],
                                     [[type(v) for v in r.values()] for r in want], "value types")
                self.assertEqual(given, rows, "input mutated")

    def test_rows_are_copies(self):
        rows = [{"a": 1}]
        out = get("limit")(rows, n=1)
        out[0]["a"] = 99
        self.assertEqual(rows, [{"a": 1}])


class Registry(unittest.TestCase):
    def test_names(self):
        self.assertEqual(names(), sorted(OPS))

    def test_unknown_and_duplicate(self):
        with self.assertRaises(OpError):
            get("nope")
        with self.assertRaises(OpError):
            register("select", lambda rows: rows)

    def test_is_value_error(self):
        self.assertTrue(issubclass(OpError, ValueError))

    def test_modules(self):
        import importlib
        for op in OPS:
            self.assertTrue(callable(importlib.import_module("dataops.ops." + op).run), op)


class Pipeline(unittest.TestCase):
    def test_run(self):
        steps = [{"op": "filter_eq", "field": "a", "value": 1}, {"op": "select", "fields": ["b"]}]
        self.assertEqual(run_pipeline(copy.deepcopy(R), steps), [{"b": "x"}, {"b": "z"}])

    def test_error_prefix(self):
        steps = [{"op": "limit", "n": 5}, {"op": "select", "fields": ["zz"]}]
        with self.assertRaises(OpError) as cm:
            run_pipeline(copy.deepcopy(R), steps)
        self.assertTrue(str(cm.exception).startswith("step 2 (select): "), str(cm.exception))

    def test_unknown_op(self):
        with self.assertRaises(OpError) as cm:
            run_pipeline([], [{"op": "nope"}])
        self.assertTrue(str(cm.exception).startswith("step 1 (nope): "), str(cm.exception))


def cli(*args):
    return subprocess.run([sys.executable, "-m", "dataops", *args], capture_output=True, text=True, cwd=os.getcwd())


def tmp(obj, raw=None):
    path = os.path.join(tempfile.mkdtemp(), "f.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw if raw is not None else json.dumps(obj))
    return path


class Cli(unittest.TestCase):
    def test_run(self):
        r = cli(tmp([{"op": "group_count", "by": ["a"]}]), tmp(R))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), json.dumps([{"a": 1, "count": 2}, {"a": 2, "count": 1}], sort_keys=True))

    def test_list(self):
        r = cli("--list")
        self.assertEqual((r.returncode, r.stdout.split()), (0, sorted(OPS)))

    def test_errors(self):
        good_p, good_i = tmp([{"op": "limit", "n": 1}]), tmp(R)
        cases = [
            (tmp([{"op": "select", "fields": ["zz"]}]), good_i),
            (tmp(None, raw="{not json"), good_i),
            (good_p, tmp(None, raw="[1, 2]")),
            (good_p, tmp({"a": 1})),
            (good_p, "/nonexistent/in.json"),
            (tmp([{"op": "group_sum", "by": ["a"], "field": "v"}]), tmp([{"a": 1, "v": 1e308}, {"a": 1, "v": 1e308}])),
        ]
        for p, i in cases:
            with self.subTest(p=p, i=i):
                r = cli(p, i)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)


class Docs(unittest.TestCase):
    def test_pages_and_tests(self):
        for op in OPS:
            self.assertTrue(os.path.getsize(os.path.join("docs", "ops", op + ".md")) > 80, op)
            self.assertTrue(os.path.isfile(os.path.join("tests", "test_%s.py" % op)), op)
        self.assertTrue(os.path.isfile("README.md"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
