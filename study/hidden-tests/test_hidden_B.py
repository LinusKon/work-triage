"""Hidden acceptance test for task B (theme pipeline). Run with the run repo as cwd."""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.getcwd()
PAIRS = ["pair-%d-%s" % (i, v) for i in range(1, 9) for v in ("light", "dark")]


def expected_palette():
    r = random.Random(7)
    out = []
    for _ in range(8):
        rgb = [r.randrange(256) for _ in range(3)]
        out.append("#%02x%02x%02x" % tuple(rgb))
    return out


def lum(hexcolor):
    h = hexcolor.lstrip("#")
    chans = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def run(*args, cwd):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd)


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Regenerate in a copy so the run's own files are not trusted.
        cls.tmp = tempfile.mkdtemp()
        for d in ("gen", "tools"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(cls.tmp, d))
        os.makedirs(os.path.join(cls.tmp, "out"))
        cls.steps = [run("gen/%s.py" % name, cwd=cls.tmp) for name in ("palette", "theme", "preview")]

    def read(self, rel):
        with open(os.path.join(self.tmp, rel), encoding="utf-8") as f:
            return f.read()

    def css_vars(self):
        return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", self.read("out/theme.css")))

    def test_generators_exit_0(self):
        self.assertEqual([s.returncode for s in self.steps], [0, 0, 0])

    def test_palette(self):
        data = json.loads(self.read("out/palette.json"))
        self.assertEqual(data["seed"], 7)
        self.assertEqual([c.lower() for c in data["colors"]], expected_palette())

    def test_theme_vars(self):
        v = {k: c.lower() for k, c in self.css_vars().items()}
        for i, c in enumerate(expected_palette(), 1):
            self.assertEqual(v.get("c%d" % i), c)
        self.assertEqual(v.get("text-light"), "#ffffff")
        self.assertEqual(v.get("text-dark"), "#111111")

    def test_theme_rules(self):
        css = re.sub(r"\s+", " ", self.read("out/theme.css"))
        for i in range(1, 9):
            for v in ("light", "dark"):
                rule = re.search(r"\.pair-%d-%s\s*\{([^}]*)\}" % (i, v), css)
                self.assertIsNotNone(rule, "pair-%d-%s" % (i, v))
                body = rule.group(1)
                self.assertRegex(body, r"background\s*:\s*var\(--c%d\)" % i)
                self.assertRegex(body, r"(?<![-\w])color\s*:\s*var\(--text-%s\)" % v)

    def test_preview(self):
        html = self.read("out/preview.html")
        found = re.findall(r'data-pair="([^"]+)"', html)
        self.assertEqual(sorted(found), sorted(PAIRS))
        for p in PAIRS:
            self.assertRegex(html, r'class="[^"]*(?<![\w-])%s(?![\w-])[^"]*"' % p)

    def test_contrast_pair(self):
        for fg, bg in (("#767676", "#ffffff"), ("#ffffff", "#000000"), ("#777777", "#ffffff")):
            r = run("tools/contrast.py", fg, bg, cwd=self.tmp)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "%.2f" % ratio(fg, bg))

    def test_contrast_css(self):
        r = run("tools/contrast.py", "--css", "out/theme.css", "--min", "4.5", cwd=self.tmp)
        pal = expected_palette()
        any_fail = False
        for i, c in enumerate(pal, 1):
            for v, t in (("light", "#ffffff"), ("dark", "#111111")):
                rr = ratio(t, c)
                verdict = "PASS" if rr >= 4.5 else "FAIL"
                any_fail |= verdict == "FAIL"
                line = re.search(r"^.*pair-%d-%s\b.*$" % (i, v), r.stdout, re.M)
                self.assertIsNotNone(line, "pair-%d-%s" % (i, v))
                self.assertIn("%.2f" % rr, line.group(0))
                self.assertIn(verdict, line.group(0))
        self.assertEqual(r.returncode, 1 if any_fail else 0)

    def test_selftest(self):
        self.assertEqual(run("tools/contrast.py", "--selftest", cwd=self.tmp).returncode, 0)


class Docs(unittest.TestCase):
    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()

    def test_wcag(self):
        text = self.read("docs/wcag.md")
        self.assertIn("w3.org", text)
        self.assertIn("4.5", text)
        self.assertIn("0.05", text)
        self.assertRegex(text, r"0\.04045|0\.03928")

    def test_contrast_report(self):
        text = self.read("docs/contrast.md")
        for i, c in enumerate(expected_palette(), 1):
            for v, t in (("light", "#ffffff"), ("dark", "#111111")):
                rr = ratio(t, c)
                line = re.search(r"^.*pair-%d-%s\b.*$" % (i, v), text, re.M)
                self.assertIsNotNone(line, "pair-%d-%s" % (i, v))
                self.assertIn("%.2f" % rr, line.group(0))
                self.assertIn("PASS" if rr >= 4.5 else "FAIL", line.group(0))


if __name__ == "__main__":
    unittest.main(verbosity=1)
