"""Hidden acceptance test for task E (csvstats). Run with the run repo as cwd."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.getcwd())

from csvstats.stats import summarize  # noqa: E402


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "data.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def cli(*args):
    return subprocess.run([sys.executable, "-m", "csvstats", *args], capture_output=True, text=True, cwd=os.getcwd())


class Summarize(unittest.TestCase):
    def test_numeric(self):
        s = summarize(["x"], [["3"], ["1"], [" 2 "], [""]])["x"]
        self.assertEqual(s["type"], "numeric")
        self.assertEqual((s["count"], s["missing"]), (3, 1))
        self.assertEqual((s["min"], s["max"]), (1.0, 3.0))
        self.assertAlmostEqual(s["mean"], 2.0)
        self.assertAlmostEqual(s["median"], 2.0)

    def test_even_median(self):
        self.assertAlmostEqual(summarize(["x"], [["1"], ["2"], ["3"], ["10"]])["x"]["median"], 2.5)

    def test_scientific_and_negative(self):
        s = summarize(["x"], [["-1e2"], ["5"]])["x"]
        self.assertEqual((s["type"], s["min"]), ("numeric", -100.0))

    def test_nan_inf_are_text(self):
        for bad in ("nan", "NaN", "inf", "-Infinity"):
            with self.subTest(bad=bad):
                self.assertEqual(summarize(["x"], [["1"], [bad]])["x"]["type"], "text")

    def test_text(self):
        s = summarize(["c"], [["b"], ["a"], [" b"], ["a"], ["c"], ["  "]])["c"]
        self.assertEqual(s, {"type": "text", "count": 5, "missing": 1, "unique": 3, "top": "a"})

    def test_empty_column(self):
        self.assertEqual(summarize(["e"], [[""], [" "]])["e"], {"type": "empty", "count": 0, "missing": 2})

    def test_several_columns(self):
        r = summarize(["a", "b"], [["1", "x"], ["2", "y"]])
        self.assertEqual(set(r), {"a", "b"})
        self.assertEqual((r["a"]["type"], r["b"]["type"]), ("numeric", "text"))


class Cli(unittest.TestCase):
    def test_text_format(self):
        p = write('name,price\nb,2\na,"1"\n')
        r = cli(p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines(), [
            "name: text count=2 missing=0 unique=2 top=a",
            "price: numeric count=2 missing=0 min=1 max=2 mean=1.5 median=1.5",
        ])

    def test_json_and_columns(self):
        p = write("a,b,c\n1,x,3\n2,y,\n")
        r = cli(p, "--format", "json", "--columns", "c,a")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(set(data), {"a", "c"})
        self.assertEqual(data["c"]["missing"], 1)
        self.assertEqual(r.stdout.strip(), json.dumps(data, sort_keys=True))

    def test_columns_order_text(self):
        p = write("a,b\n1,2\n")
        r = cli(p, "--columns", "b,a")
        self.assertEqual([l.split(":")[0] for l in r.stdout.strip().splitlines()], ["b", "a"])

    def test_quoted_delimiter(self):
        p = write('a;b\n"x;y";1\n')
        r = cli(p, "--delimiter", ";", "--format", "json")
        self.assertEqual(json.loads(r.stdout)["a"]["top"], "x;y")

    def test_number_format(self):
        p = write("v\n0.1\n0.2\n1234567\n")
        line = cli(p).stdout.strip()
        self.assertIn("max=%s" % format(1234567.0, ".6g"), line)
        self.assertIn("min=0.1", line)

    def test_errors(self):
        cases = [
            write(""),
            write("a,a\n1,2\n"),
            write("a,\n1,2\n"),
            write("a,b\n1\n"),
        ]
        for p in cases:
            with self.subTest(p=open(p).read()):
                r = cli(p)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.strip())
        self.assertEqual(cli("/nonexistent/x.csv").returncode, 2)
        self.assertEqual(cli(write("a\n1\n"), "--columns", "zz").returncode, 2)

    def test_bad_row_line_number(self):
        r = cli(write("a,b\n1,2\n3\n"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("3", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
