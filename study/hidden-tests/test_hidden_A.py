"""Hidden acceptance test for task A (textkit). Run with the run repo as cwd."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.getcwd())

from textkit.slug import slugify  # noqa: E402
from textkit.words import word_count, top_words  # noqa: E402
from textkit.readtime import reading_time  # noqa: E402


def cli(*args):
    return subprocess.run([sys.executable, "-m", "textkit", *args], capture_output=True, text=True, cwd=os.getcwd())


class Slug(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_accents_dropped_not_split(self):
        self.assertEqual(slugify("Crème Brûlée"), "creme-brulee")

    def test_non_ascii_removed(self):
        self.assertEqual(slugify("日本 abc"), "abc")

    def test_runs_and_ends(self):
        self.assertEqual(slugify("  --a__b  c--  "), "a-b-c")

    def test_cut_strips_trailing_dash(self):
        self.assertEqual(slugify("abc def", max_len=4), "abc")

    def test_cut_exact(self):
        self.assertEqual(slugify("abcdef", max_len=3), "abc")

    def test_default_len(self):
        self.assertEqual(len(slugify("a" * 80)), 50)

    def test_empty(self):
        self.assertEqual(slugify("!!!"), "")

    def test_bad_len(self):
        with self.assertRaises(ValueError):
            slugify("a", max_len=0)

    def test_bad_type(self):
        with self.assertRaises(TypeError):
            slugify(None)


class Words(unittest.TestCase):
    def test_count(self):
        self.assertEqual(word_count("It's a dog's life, isn't it?"), 6)

    def test_underscore_splits(self):
        self.assertEqual(word_count("snake_case"), 2)

    def test_unicode_letters(self):
        self.assertEqual(word_count("über straße"), 2)

    def test_digits(self):
        self.assertEqual(word_count("3 apples and 42"), 4)

    def test_empty(self):
        self.assertEqual(word_count("  ... "), 0)

    def test_count_type(self):
        with self.assertRaises(TypeError):
            word_count(3)

    def test_top_order(self):
        self.assertEqual(top_words("b a B c a b", 2), [("b", 3), ("a", 2)])

    def test_top_ties_alpha(self):
        self.assertEqual(top_words("z y x", 5), [("x", 1), ("y", 1), ("z", 1)])

    def test_top_zero(self):
        self.assertEqual(top_words("a b", 0), [])

    def test_top_negative(self):
        with self.assertRaises(ValueError):
            top_words("a", -1)

    def test_top_tuples(self):
        result = top_words("a a", 1)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], ("a", 2))


class ReadTime(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(reading_time(""), 0)

    def test_one_word(self):
        self.assertEqual(reading_time("word"), 1)

    def test_ceil(self):
        self.assertEqual(reading_time("w " * 201), 2)

    def test_exact(self):
        self.assertEqual(reading_time("w " * 200), 1)

    def test_wpm(self):
        self.assertEqual(reading_time("a b c", wpm=2), 2)

    def test_bad_wpm(self):
        for wpm in (0, -5):
            with self.assertRaises(ValueError):
                reading_time("a", wpm=wpm)


class Cli(unittest.TestCase):
    def test_slugify(self):
        r = cli("slugify", "Hello World", "--max-len", "5")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "hello"))

    def test_reading_time(self):
        r = cli("reading-time", "a b c", "--wpm", "2")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "2"))

    def test_word_count(self):
        r = cli("word-count", "one two")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "2"))

    def test_top_words(self):
        r = cli("top-words", "b a b", "-n", "2")
        self.assertEqual((r.returncode, r.stdout.strip().splitlines()), (0, ["b 2", "a 1"]))

    def test_top_words_default(self):
        r = cli("top-words", "a b c d e f g")
        self.assertEqual(len(r.stdout.strip().splitlines()), 5)

    def test_value_error_exit_2(self):
        r = cli("slugify", "x", "--max-len", "0")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.strip())

    def test_bad_command_exit_2(self):
        self.assertEqual(cli("nope").returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
