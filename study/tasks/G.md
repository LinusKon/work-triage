Build `safestore`, a store for uploaded files, in this repository: Python 3.9 standard library only, tests with
`unittest` under `tests/`. Run to the user gate and stop. The interface is fixed:

- `safestore/errors.py`: `class StoreError(Exception)`. No message ever contains the store's absolute root path.
- `safestore/store.py`: `class Store(root, max_bytes=5_000_000)`.
  - `save(filename: str, data: bytes) -> dict` returns `{"id", "name", "type", "size"}`:
    - `size` is `len(data)`; it must be between 1 and `max_bytes` inclusive, else `StoreError`.
    - `type` is detected from the content only: `png` (data starts with `b"\x89PNG\r\n\x1a\n"`), `jpeg`
      (`b"\xff\xd8\xff"`), `pdf` (`b"%PDF-"`); anything else raises `StoreError`.
    - `name` is the sanitised filename: take the part after the last `/` or `\`, NFKC-normalise it, replace every
      run of characters outside `A-Za-z0-9._-` with one `_`, strip leading `.` characters, cut to 100 characters;
      an empty result becomes `file`. Its extension (after the last `.`, case-insensitive) must match the type:
      `png`; `jpg` or `jpeg`; `pdf`. A missing or other extension raises `StoreError`.
    - `id` is the lowercase hex SHA-256 of `data`. The bytes are written to `<root>/<id[:2]>/<id>` through a
      temporary file in the same folder and `os.replace`, so a reader never sees a partial file; saving the same
      content twice is allowed and keeps one file. No temporary file is left behind.
  - `open(id) -> bytes` returns the stored bytes. An `id` that is not exactly 64 lowercase hex characters, or that
    is not stored, raises `StoreError`. No path outside `root` is ever read or written.

Steps: 1. `safestore/errors.py` and `safestore/store.py` with tests, covering every rule above. 2. `docs/security.md`:
the threats the rules address (path traversal, type spoofing, oversized uploads, partial writes) in a few lines
each. 3. Push and open the PR (no remote: a user gate).
