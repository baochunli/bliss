from __future__ import annotations

import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]


class BlissBookClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.class_source = (SOURCE_DIR / "blissbook.cls").read_text(encoding="utf-8")

    def test_subsection_headers_are_left_aligned(self) -> None:
        start = self.class_source.index(r"\newcommand{\BookSubtitle}")
        end = self.class_source.index("\n\\newcommand", start + 1)
        definition = self.class_source[start:end]

        self.assertIn(r"\par\vspace{14bp}", definition)
        self.assertIn(r"\noindent\hspace{\parindent}", definition)
        self.assertIn(r"\BlissHeadingFont\fontsize{11bp}{18.7bp}\selectfont #1", definition)
        self.assertIn(r"\begingroup", definition)
        self.assertIn(r"\endgroup", definition)
        self.assertNotIn(r"\makebox[\textwidth][c]", definition)
        self.assertNotIn(r"\centering", definition)

    def test_subsection_headers_stay_with_the_first_following_line(self) -> None:
        subtitle_start = self.class_source.index(r"\newcommand{\BookSubtitle}")
        subtitle_end = self.class_source.index("\n\\newcommand", subtitle_start + 1)
        subtitle = self.class_source[subtitle_start:subtitle_end]

        paragraph_start = self.class_source.index(r"\newcommand{\BookParagraph}")
        paragraph_end = self.class_source.index("\n\\newcommand", paragraph_start + 1)
        paragraph = self.class_source[paragraph_start:paragraph_end]

        self.assertIn(r"\nobreak\vspace{7bp}\nobreak", subtitle)
        self.assertIn(r"\global\BlissAfterSubtitletrue", subtitle)
        self.assertIn(r"\clubpenalty=0", paragraph)
        self.assertIn(r"\global\BlissAfterSubtitlefalse", paragraph)


if __name__ == "__main__":
    unittest.main()
