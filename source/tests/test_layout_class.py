from __future__ import annotations

import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]


class BlissBookClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.class_source = (SOURCE_DIR / "blissbook.cls").read_text(encoding="utf-8")

    def command_definition(self, command: str) -> str:
        start = self.class_source.index(rf"\newcommand{{\{command}}}")
        end = self.class_source.find("\n\\newcommand", start + 1)
        if end == -1:
            end = len(self.class_source)
        return self.class_source[start:end]

    def test_compact_body_leading_preserves_paragraph_spacing(self) -> None:
        self.assertIn(
            r"\newcommand{\BookBodyFont}{\fontsize{11bp}{16.5bp}\selectfont}",
            self.class_source,
        )
        self.assertIn(r"\setlength{\parskip}{5pt}", self.class_source)

    def test_articles_flow_continuously_with_guarded_compact_titles(self) -> None:
        definition = self.command_definition("BookArticle")

        self.assertIn(r"\RequirePackage{needspace}", self.class_source)
        ordered_tokens = (
            r"\par",
            r"\Needspace{140bp}",
            r"\vspace*{15bp}",
            r"\noindent\makebox[\textwidth][c]",
            r"\vspace{15bp}",
            r"\BookBodyFont",
        )
        positions = [definition.index(token) for token in ordered_tokens]
        self.assertEqual(sorted(positions), positions)
        self.assertNotIn(r"\clearpage", definition)
        self.assertNotIn(r"\cleardoublepage", definition)

    def test_part_dividers_do_not_force_recto_body_pages(self) -> None:
        definition = self.command_definition("BookPart")
        divider_tail = definition[definition.index(r"\end{minipage}") :]

        self.assertEqual(r"\cleardoublepage", definition.splitlines()[1].strip())
        self.assertIn("\n  \\clearpage\n", divider_tail)
        self.assertNotIn(r"\cleardoublepage", divider_tail)

    def test_book_ends_with_two_blank_pages(self) -> None:
        definition = self.command_definition("BookFinish")

        self.assertEqual(2, definition.count(r"\thispagestyle{empty}\null\clearpage"))
        self.assertNotIn(r"\ReadonlyShipoutCounter", definition)

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

    def test_english_em_dash_uses_the_latin_body_font(self) -> None:
        self.assertIn(
            r'\newcommand{\LatinEmDash}{{\BlissColophonLatin\ltjalchar"2014}}',
            self.class_source,
        )

    def test_reader_questions_use_body_paragraph_typography(self) -> None:
        self.assertIn(
            r"\newcommand{\BookQuestion}[1]{\BookParagraph{#1}}",
            self.class_source,
        )

    def test_markdown_hard_breaks_do_not_stretch_short_lines(self) -> None:
        self.assertIn(
            r"\newcommand{\BookHardBreak}{\newline}",
            self.class_source,
        )
        self.assertIn(
            r"\newcommand{\BookLineBreak}{\linebreak}",
            self.class_source,
        )


if __name__ == "__main__":
    unittest.main()
