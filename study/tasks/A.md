Build `textkit` in this repository: Python 3.9 standard library only, tests with `unittest` under `tests/`.
Run to the user gate and stop. The public interface is fixed:

- `textkit.slug.slugify(text, max_len=50) -> str`: NFKD-normalise, drop non-ASCII characters, lowercase,
  replace every run of characters outside `a-z0-9` with one `-`, strip `-` at both ends; if the result is
  longer than `max_len`, cut it to `max_len` characters and strip trailing `-` again. `max_len < 1` raises
  `ValueError`; a non-`str` `text` raises `TypeError`.
- `textkit.words.word_count(text) -> int`: a word is a match of the regex `[^\W_]+(?:'[^\W_]+)*` (Unicode).
  A non-`str` `text` raises `TypeError`.
- `textkit.words.top_words(text, n) -> list[tuple[str, int]]`: words as above, lowercased, counted, sorted by
  count descending then word ascending, the first `n`. `n < 0` raises `ValueError`; `n == 0` returns `[]`.
- `textkit.readtime.reading_time(text, wpm=200) -> int`: whole minutes, `ceil(word_count(text) / wpm)`; `0`
  when there are no words. `wpm <= 0` raises `ValueError`.
- CLI `python3 -m textkit <command>`: `slugify TEXT [--max-len N]` prints the slug; `reading-time TEXT
  [--wpm N]` prints the minutes; `word-count TEXT` prints the count; `top-words TEXT [-n N]` (default 5)
  prints one `word count` line per word. Invalid arguments or a `ValueError` exit with status 2 and a message
  on stderr.

Steps: 1. Record this interface and anything it leaves open in `docs/interface.md`. 2. `textkit/slug.py` with
tests. 3. `textkit/readtime.py` with tests. 4. `textkit/words.py` with tests. 5. `textkit/__main__.py` with
tests. 6. README usage section, one runnable example per function. 7. Push and open the PR (no remote: a
user gate).
