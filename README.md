# Regex Delimiter Splitter

Splits a string on regex matches and returns each piece — delimiter or gap — with its start/end offsets and captured groups.

```python
from regex_delimiter_splitter import split, SplitPart

parts = split(r"(\w+)=(\d+)", "x foo=42 y")
for p in parts:
    print(p.is_match, p.text, p.start, p.end, p.groups)
# False x          0 1 ()
# True  foo=42     1 7  ('foo=42', 'foo', '42')
# False  y         7 9 ()
```

`split(pattern, text)` accepts a string pattern or a compiled `re.Pattern`. It returns a list of `SplitPart(text, start, end, is_match, groups)`. `is_match=True` marks a delimiter segment; `groups` is a tuple whose first element is the full match text followed by capture groups in order (or `None` for non-participating groups). Gap segments have an empty `groups` tuple.

## Why this exists

`re.split` discards match positions and, by default, the delimiters themselves. When you need both — e.g. to reconstruct or transform text while knowing exactly where each delimiter sat and what it captured — you end up re-running `finditer` and gluing logic onto it. This library is that glue, packaged and tested.

The trade-off: there is no `maxsplit` parameter. `re.split`'s `maxsplit` counts delimiters, which makes the tail-piece semantics ambiguous for a position-and-group-preserving API. Rather than pick one interpretation silently, the library splits on every match. If you need a limited split, slice the result.

## Edge cases

Adjacent matches produce an **empty gap segment** between them, so the result list alternates match / gap strictly. This guarantees that joining all `text` fields reconstructs the input exactly, but it means `len(parts)` can exceed the count you'd get from `re.split`. Zero-width matches (including the empty pattern `""`) are supported and terminate correctly; the match segments they produce have `start == end`.
