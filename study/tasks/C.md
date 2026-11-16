Build a webhook verifier in this repository: Python 3.9 standard library only, tests with `unittest` under
`tests/`. Run to the user gate and stop. The interface is fixed:

- `webhooks/errors.py`: `class VerificationError(Exception)` and `class ConfigError(Exception)`.
- `webhooks/store.py`: `class MemoryNonceStore(ttl: int)` with `add(nonce: str, now: int) -> bool`: `True`
  when the nonce is new or its earlier entry is older than `ttl` seconds (then it is recorded with `now`),
  `False` when it was added within the last `ttl` seconds. Expired entries are pruned.
- `webhooks/verify.py`: `verify(body: bytes, headers, *, secret: bytes, now: int, store, tolerance=300) ->
  None`. `headers` is a mapping whose names compare case-insensitively. Required headers: `X-Timestamp`
  (decimal integer seconds, at most 12 digits), `X-Nonce` (1 to 64 characters from `A-Za-z0-9_-`; any other
  nonce is rejected), `X-Signature`: a comma-separated list of `scheme=value`
  entries; only `v1` entries count, each the lowercase hex HMAC-SHA256 of
  `f"{timestamp}.{nonce}.".encode() + body` keyed with `secret`. The request is valid when any `v1` entry
  matches (constant-time comparison), `abs(now - timestamp) <= tolerance`, and `store.add(nonce, now)` returns
  `True`; the nonce is recorded only after the signature and timestamp have passed. Every failure raises
  `VerificationError`; its message never contains the secret or the expected signature.
- `webhooks/config.py`: `load_secret(env=None) -> bytes` reads `WEBHOOK_SECRET` from `env` (default
  `os.environ`) and returns it UTF-8 encoded; missing or empty raises `ConfigError`, whose message names the
  variable but never a value.

Steps: 1. `webhooks/errors.py` and `webhooks/store.py` with tests. 2. `webhooks/verify.py` with tests,
including replay, tolerance edges, header case, several signatures and tampered bodies. 3.
`webhooks/config.py` with tests. 4. `docs/operations.md`: how to run the service with the secret supplied
through the environment (for example a 1Password `op run` reference), never a value in a file. 5. Push and
open the PR (no remote: a user gate).
