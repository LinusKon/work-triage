"""Hidden acceptance test for task C (webhook verifier). Run with the run repo as cwd."""
import hashlib
import hmac
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from webhooks.errors import VerificationError, ConfigError  # noqa: E402
from webhooks.store import MemoryNonceStore  # noqa: E402
from webhooks.verify import verify  # noqa: E402
from webhooks.config import load_secret  # noqa: E402

SECRET = b"s3cr3t-key-material"
NOW = 1_700_000_000


def sign(ts, nonce, body, secret=SECRET):
    return hmac.new(secret, ("%s.%s." % (ts, nonce)).encode() + body, hashlib.sha256).hexdigest()


def headers(ts=NOW, nonce="n1", body=b"{}", sig=None, case=str):
    sig = sig if sig is not None else "v1=" + sign(ts, nonce, body)
    return {case("X-Timestamp"): str(ts), case("X-Nonce"): nonce, case("X-Signature"): sig}


class Store(unittest.TestCase):
    def test_new_then_replay(self):
        s = MemoryNonceStore(300)
        self.assertTrue(s.add("a", 100))
        self.assertFalse(s.add("a", 200))

    def test_expiry_boundary(self):
        s = MemoryNonceStore(300)
        self.assertTrue(s.add("a", 100))
        self.assertFalse(s.add("a", 400))
        self.assertTrue(s.add("a", 401))

    def test_independent(self):
        s = MemoryNonceStore(10)
        self.assertTrue(s.add("a", 0))
        self.assertTrue(s.add("b", 0))


class Verify(unittest.TestCase):
    def ok(self, body=b"{}", **kw):
        store = kw.pop("store", MemoryNonceStore(300))
        verify(body, headers(body=body, **kw), secret=SECRET, now=kw.get("ts", NOW), store=store)

    def bad(self, body, hdrs, now=NOW, store=None, secret=SECRET):
        with self.assertRaises(VerificationError) as cm:
            verify(body, hdrs, secret=secret, now=now, store=store or MemoryNonceStore(300))
        msg = str(cm.exception)
        self.assertNotIn(SECRET.decode(), msg)
        self.assertNotIn(sign(hdrs.get("X-Timestamp", NOW), hdrs.get("X-Nonce", ""), body), msg)
        return cm.exception

    def test_valid(self):
        self.assertIsNone(verify(b"{}", headers(), secret=SECRET, now=NOW, store=MemoryNonceStore(300)))

    def test_header_case(self):
        verify(b"{}", headers(case=str.lower), secret=SECRET, now=NOW, store=MemoryNonceStore(300))
        verify(b"{}", headers(nonce="n2", case=str.upper), secret=SECRET, now=NOW, store=MemoryNonceStore(300))

    def test_tampered_body(self):
        self.bad(b'{"a":1}', headers(body=b"{}"))

    def test_wrong_secret(self):
        self.bad(b"{}", headers(), secret=b"other")

    def test_missing_headers(self):
        for name in ("X-Timestamp", "X-Nonce", "X-Signature"):
            h = headers()
            del h[name]
            self.bad(b"{}", h)

    def test_empty_nonce(self):
        self.bad(b"{}", headers(nonce=""))

    def test_non_int_timestamp(self):
        h = headers()
        h["X-Timestamp"] = "12.5"
        self.bad(b"{}", h)

    def test_nonce_charset_and_length(self):
        for nonce in ("a.b", "a b", "ä", "x" * 65):
            with self.subTest(nonce=nonce):
                self.bad(b"{}", headers(nonce=nonce))
        verify(b"{}", headers(nonce="A-z_0" + "9" * 59), secret=SECRET, now=NOW, store=MemoryNonceStore(300))

    def test_timestamp_digits(self):
        h = headers()
        h["X-Timestamp"] = "1" * 13
        self.bad(b"{}", h)

    def test_tolerance_edges(self):
        verify(b"{}", headers(ts=NOW - 300), secret=SECRET, now=NOW, store=MemoryNonceStore(300))
        verify(b"{}", headers(ts=NOW + 300, nonce="n2"), secret=SECRET, now=NOW, store=MemoryNonceStore(300))
        self.bad(b"{}", headers(ts=NOW - 301))
        self.bad(b"{}", headers(ts=NOW + 301))

    def test_custom_tolerance(self):
        with self.assertRaises(VerificationError):
            verify(b"{}", headers(ts=NOW - 11), secret=SECRET, now=NOW, store=MemoryNonceStore(300), tolerance=10)

    def test_replay(self):
        store = MemoryNonceStore(300)
        verify(b"{}", headers(), secret=SECRET, now=NOW, store=store)
        self.bad(b"{}", headers(), store=store)

    def test_nonce_not_recorded_on_bad_signature(self):
        store = MemoryNonceStore(300)
        self.bad(b"{}", headers(sig="v1=" + "0" * 64), store=store)
        verify(b"{}", headers(), secret=SECRET, now=NOW, store=store)

    def test_nonce_not_recorded_on_stale_timestamp(self):
        store = MemoryNonceStore(300)
        stale = headers(ts=NOW - 1000)
        self.bad(b"{}", stale, store=store)
        verify(b"{}", headers(), secret=SECRET, now=NOW, store=store)

    def test_several_signatures(self):
        good = sign(NOW, "n1", b"{}")
        verify(b"{}", headers(sig="v1=%s,v1=%s" % ("ab" * 32, good)), secret=SECRET, now=NOW,
               store=MemoryNonceStore(300))
        verify(b"{}", headers(nonce="n2", sig="v0=zz, v1=%s" % sign(NOW, "n2", b"{}")), secret=SECRET,
               now=NOW, store=MemoryNonceStore(300))

    def test_only_other_schemes(self):
        self.bad(b"{}", headers(sig="v0=" + sign(NOW, "n1", b"{}")))

    def test_bad_hex(self):
        self.bad(b"{}", headers(sig="v1=zz"))

    def test_uppercase_hex_still_compares(self):
        # The spec fixes lowercase hex; an uppercase copy of the right digest must not pass as a different value
        # in a way that crashes: either accepted or VerificationError, never another exception.
        try:
            verify(b"{}", headers(sig="v1=" + sign(NOW, "n1", b"{}").upper()), secret=SECRET, now=NOW,
                   store=MemoryNonceStore(300))
        except VerificationError:
            pass

    def test_constant_time_used(self):
        import webhooks.verify as mod
        src = open(mod.__file__, encoding="utf-8").read()
        self.assertIn("compare_digest", src)


class Config(unittest.TestCase):
    def test_load(self):
        self.assertEqual(load_secret({"WEBHOOK_SECRET": "abc"}), b"abc")

    def test_utf8(self):
        self.assertEqual(load_secret({"WEBHOOK_SECRET": "ä"}), "ä".encode("utf-8"))

    def test_missing(self):
        with self.assertRaises(ConfigError) as cm:
            load_secret({})
        self.assertIn("WEBHOOK_SECRET", str(cm.exception))

    def test_empty(self):
        with self.assertRaises(ConfigError):
            load_secret({"WEBHOOK_SECRET": ""})

    def test_default_environ(self):
        old = os.environ.get("WEBHOOK_SECRET")
        os.environ["WEBHOOK_SECRET"] = "from-env"
        try:
            self.assertEqual(load_secret(), b"from-env")
        finally:
            if old is None:
                del os.environ["WEBHOOK_SECRET"]
            else:
                os.environ["WEBHOOK_SECRET"] = old


class Docs(unittest.TestCase):
    def test_operations(self):
        text = open(os.path.join(os.getcwd(), "docs/operations.md"), encoding="utf-8").read()
        self.assertIn("WEBHOOK_SECRET", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
