"""Hidden acceptance test for task G (safestore). Run with the run repo as cwd."""
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.getcwd())

from safestore.errors import StoreError  # noqa: E402
from safestore.store import Store  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"rest-of-png"
JPG = b"\xff\xd8\xff" + b"jpeg-body"
PDF = b"%PDF-1.7 body"


class Base(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.store = Store(self.root, max_bytes=64)

    def bad(self, *args, method="save"):
        with self.assertRaises(StoreError) as cm:
            getattr(self.store, method)(*args)
        self.assertNotIn(self.root, str(cm.exception))


class Save(Base):
    def test_png(self):
        r = self.store.save("photo.png", PNG)
        sid = hashlib.sha256(PNG).hexdigest()
        self.assertEqual(r, {"id": sid, "name": "photo.png", "type": "png", "size": len(PNG)})
        self.assertTrue(os.path.isfile(os.path.join(self.root, sid[:2], sid)))
        self.assertEqual(self.store.open(sid), PNG)

    def test_types_and_extensions(self):
        self.assertEqual(self.store.save("a.JPG", JPG)["type"], "jpeg")
        self.assertEqual(self.store.save("b.jpeg", JPG)["type"], "jpeg")
        self.assertEqual(self.store.save("c.Pdf", PDF)["type"], "pdf")

    def test_extension_mismatch(self):
        self.bad("x.pdf", PNG)
        self.bad("x", PNG)
        self.bad("x.png.exe", PNG)

    def test_unknown_content(self):
        self.bad("x.png", b"GIF89a....")
        self.bad("x.png", b"\x89PNG")

    def test_size_limits(self):
        self.bad("x.png", b"")
        self.store.save("ok.png", PNG + b"a" * (64 - len(PNG)))
        self.bad("x.png", PNG + b"a" * (65 - len(PNG)))

    def test_traversal_names(self):
        self.assertEqual(self.store.save("../../etc/passwd.png", PNG)["name"], "passwd.png")
        self.assertEqual(self.store.save("..\\..\\win\\evil.png", PNG)["name"], "evil.png")
        self.assertEqual(self.store.save("...hidden.png", PNG)["name"], "hidden.png")
        for dirpath, _, files in os.walk(self.root):
            self.assertTrue(os.path.realpath(dirpath).startswith(self.root))

    def test_sanitise(self):
        self.assertEqual(self.store.save("my photo (1).png", PNG)["name"], "my_photo_1_.png")
        self.assertEqual(self.store.save("ｆｕｌｌ.png", PNG)["name"], "full.png")
        long = "a" * 120 + ".png"
        self.bad(long, PNG)  # cut to 100 characters drops the extension
        self.assertEqual(len(self.store.save("a" * 96 + ".png", PNG)["name"]), 100)

    def test_idempotent_and_no_temp(self):
        a = self.store.save("a.png", PNG)
        b = self.store.save("b.png", PNG)
        self.assertEqual(a["id"], b["id"])
        files = [f for _, _, fs in os.walk(self.root) for f in fs]
        self.assertEqual(files, [a["id"]])


class Open(Base):
    def test_bad_ids(self):
        for sid in ("../x", "A" * 64, "a" * 63, "a" * 65, "g" * 64, "../" + "a" * 61):
            with self.subTest(sid=sid):
                self.bad(sid, method="open")

    def test_missing(self):
        self.bad("a" * 64, method="open")


class Docs(unittest.TestCase):
    def test_security_doc(self):
        text = open(os.path.join(os.getcwd(), "docs/security.md"), encoding="utf-8").read().lower()
        for word in ("traversal", "spoof", "partial"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
