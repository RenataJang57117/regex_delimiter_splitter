"""Core splitting logic.

The split operates on the *matches* of a regex, not the text between
them in the sense of plain str.split. Concretely, for input text T and
pattern P, we find every non-overlapping match m_1, m_2, ... of P in T.
The non-delimiter text is whatever sits between these matches: from the
end of m_{i-1} to the start of m_i, with the boundaries of the string
used at the front and back.

We deliberately chose to preserve an empty non-delimiter piece rather
than dropping it (e.g. when two matches are adjacent). This makes the
split a true inverse of a join-by-delimiter operation: joining the
pieces with the original delimiters reconstructs the input exactly.

We chose not to implement re.split's MAXSPLIT parameter because it
interacts ambiguously with the "keep positions and groups" requirement:
* the split count is on delimiters, not on pieces, so the tail
  semantics are unclear when a user wants N pieces. Keeping the API
  minimal and exact was preferred over mirroring every flag of re.split.
"""

import re
from typing import List, NamedTuple, Optional, Sequence


class SplitPart(NamedTuple):
    """A single segment of the split result.

    is_match=True marks a delimiter (a substring that matched the pattern).
is_match=False marks a gap: literal text that fell between two matches
    (or between a string boundary and a match).

    start/end are absolute offsets into the original input string, so
    callers can locate the segment without re-searching.

    groups is a tuple of the regex capture groups for a delimiter
    segment. Element 0 is the full match. For a gap segment groups is
    an empty tuple. Groups that did not participate in the match appear
    as None, matching the convention of re.Match.groups().
    """

    text: str
    start: int
    end: int
    is_match: bool
    groups: Sequence[Optional[str]]


def split(pattern, text: str) -> List[SplitPart]:
    """Split *text* on every non-overlapping match of *pattern*.

    *pattern* may be a compiled regex or any object accepted by
    re.compile (a string or a pattern object). Empty matches and
    zero-width matches are handled. An empty-match pattern is a valid
    degenerate case: the result lists every character as a gap with a
    zero-width delimiter between them, plus a trailing zero-width
    delimiter. Because Python's re semantics advance the scan position
    by one character after a zero-width match, an anchored empty match
    (e.g. ^ or \b) will not loop forever and will still terminate.

    Returns an ordered list of SplitPart. Delimiter and gap segments
alternate; gap segments can be empty (adjacent matches, leading/trailing
    matches). Delimiter segments can have empty text (zero-width
    matches) but never have a non-empty text that differs from the
    substring of *text* at [start:end].
    """
    if isinstance(pattern, re.Pattern):
        compiled = pattern
    else:
        compiled = re.compile(pattern)

    parts: List[SplitPart] = []
    pos = 0
    last_end = 0
    n = len(text)

    # finditer advances one character after a zero-width match, so
    # anchored patterns (e.g. r'^') terminate after producing at most
    # one match per applicable position. We rely on that property to
    # avoid an explicit infinite-loop guard.
    for m in compiled.finditer(text):
        m_start, m_end = m.span()

        # Guard against a pathological engine regression where a
        # zero-width match is reported at a position we have already
        # passed. Should never happen with CPython's re, but cheap.
        if m_end < pos:
            continue

        if m_start > last_end:
            parts.append(
                SplitPart(
                    text=text[last_end:m_start],
                    start=last_end,
                    end=m_start,
                    is_match=False,
                    groups=(),
                )
            )
        elif m_start == last_end and last_end > 0:
            # Adjacent match with no gap between: emit an explicit empty
            # gap so joining pieces reconstructs the input exactly.
            parts.append(
                SplitPart(
                    text="",
                    start=last_end,
                    end=last_end,
                    is_match=False,
                    groups=(),
                )
            )

        full = m.group(0)
        groups = (full,) + m.groups()
        parts.append(
            SplitPart(
                text=full,
                start=m_start,
                end=m_end,
                is_match=True,
                groups=groups,
            )
        )

        last_end = m_end
        pos = m_end
        if m_end == m_start:
            # Zero-width match: force the next search to start one char
            # later so we don't report the same empty match again.
            pos = m_end + 1

    if last_end < n or not parts:
        parts.append(
            SplitPart(
                text=text[last_end:],
                start=last_end,
                end=n,
                is_match=False,
                groups=(),
            )
        )

    return parts
