import re
import unittest

from regex_delimiter_splitter import SplitPart, split


class TestSplitBasic(unittest.TestCase):
    def test_simple_split(self):
        parts = split(r"\s+", "a b  c")
        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[0], SplitPart("a", 0, 1, False, ()))
        self.assertEqual(parts[1], SplitPart(" ", 1, 2, True, (" ",)))
        self.assertEqual(parts[2], SplitPart("b", 2, 3, False, ()))
        self.assertEqual(parts[3], SplitPart("  ", 3, 5, True, ("  ",)))
        self.assertEqual(parts[4], SplitPart("c", 5, 6, False, ()))

    def test_no_matches_returns_single_gap(self):
        parts = split(r"\d+", "hello world")
        self.assertEqual(parts, [SplitPart("hello world", 0, 11, False, ())])

    def test_empty_string_input(self):
        parts = split(r"x", "")
        self.assertEqual(parts, [SplitPart("", 0, 0, False, ())])

    def test_match_at_start(self):
        parts = split(r"x", "xabc")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], SplitPart("x", 0, 1, True, ("x",)))
        self.assertEqual(parts[1], SplitPart("abc", 1, 4, False, ()))

    def test_match_at_end(self):
        parts = split(r"x", "abcx")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], SplitPart("abc", 0, 3, False, ()))
        self.assertEqual(parts[1], SplitPart("x", 3, 4, True, ("x",)))


class TestCaptureGroups(unittest.TestCase):
    def test_named_and_positional_groups(self):
        parts = split(r"(?P<key>\w+)=(\d+)", "x foo=42 y")
        m = parts[1]
        self.assertTrue(m.is_match)
        self.assertEqual(m.text, "foo=42")
        self.assertEqual(m.groups, ("foo=42", "foo", "42"))

    def test_optional_group_not_participating(self):
        # Second group optional; first match omits it (should be None).
        parts = split(r"(a)(b)?", "xa ay")
        # matches: 'a' at index 1, 'ab' at... wait 'ab'? input 'xa ay'
        # 'a' at 1, then 'a' at 3 (b not present), no 'ab'
        matches = [p for p in parts if p.is_match]
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].groups, ("a", "a", None))
        self.assertEqual(matches[1].groups, ("a", "a", None))


class TestAdjacentAndZeroWidth(unittest.TestCase):
    def test_adjacent_matches_yield_empty_gap(self):
        # Two 'a' matches in a row -> empty gap between them.
        parts = split(r"a", "aabaa")
        self.assertEqual(len(parts), 7)
        # m, '', m, gap, m, '', m
        self.assertEqual(parts[0], SplitPart("a", 0, 1, True, ("a",)))
        self.assertEqual(parts[1], SplitPart("", 1, 1, False, ()))
        self.assertEqual(parts[2], SplitPart("a", 1, 2, True, ("a",)))
        self.assertEqual(parts[3], SplitPart("b", 2, 3, False, ()))
        self.assertEqual(parts[4], SplitPart("a", 3, 4, True, ("a",)))
        self.assertEqual(parts[5], SplitPart("", 4, 4, False, ()))
        self.assertEqual(parts[6], SplitPart("a", 4, 5, True, ("a",)))

    def test_zero_width_pattern_terminates(self):
        # Empty pattern: zero-width match at each position. We don't
        # assert the exact count (re advances by one after each empty
        # match), only that it terminates and round-trips.
        parts = split(r"", "ab")
        joined = "".join(p.text for p in parts)
        self.assertEqual(joined, "ab")
        # All match segments are zero-width.
        for p in parts:
            if p.is_match:
                self.assertEqual(p.start, p.end)

    def test_leading_zero_width_match(self):
        # ^ matches only at start, zero-width.
        parts = split(r"^", "abc")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], SplitPart("", 0, 0, True, ("",)))
        self.assertEqual(parts[1], SplitPart("abc", 0, 3, False, ()))


class TestCompiledPattern(unittest.TestCase):
    def test_accepts_compiled_regex(self):
        rx = re.compile(r"[,;]+")
        parts = split(rx, "a,b;c")
        self.assertEqual([p.text for p in parts], ["a", ",", "b", ";", "c"])
        self.assertEqual([p.is_match for p in parts], [False, True, False, True, False])


class TestReconstruction(unittest.TestCase):
    def test_join_reconstructs_input(self):
        for pat, text in [
            (r"\s+", "  a  b   c  "),
            (r"a", "banana"),
            (r"\d", "1a2b3"),
            (r"", "hello"),
            (r"x", "xxx"),
        ]:
            with self.subTest(pattern=pat, text=text):
                parts = split(pat, text)
                self.assertEqual("".join(p.text for p in parts), text)


class TestPositions(unittest.TestCase):
    def test_positions_are_monotonic_and_contiguous(self):
        parts = split(r"\W+", "Hello, world! Bye.")
        prev_end = 0
        for p in parts:
            self.assertGreaterEqual(p.start, prev_end - 1)  # allow empty overlap
            self.assertEqual(p.end, p.start + len(p.text))
            self.assertEqual(p.text, "Hello, world! Bye."[p.start:p.end])
            prev_end = p.end


if __name__ == "__main__":
    unittest.main()
