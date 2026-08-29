from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SOURCE_DIR.parent
INDESIGN_DIR = PROJECT_DIR / "indesign"
sys.path.insert(0, str(SOURCE_DIR / "scripts"))

from convert_idml import extract_book, render_content_tex, render_manifest  # noqa: E402


class ConvertIdmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.idml_path = INDESIGN_DIR / "Bliss Pages Final Edition.idml"
        cls.book = extract_book(cls.idml_path)

    def test_extracts_authoritative_toc_order(self) -> None:
        entries = [article for part in self.book.parts for article in part.articles]

        self.assertEqual(8, len(self.book.parts))
        self.assertEqual(133, len(entries))
        self.assertEqual("幸福", self.book.parts[0].title)
        self.assertEqual("柴米油盐酱醋茶", self.book.parts[-1].title)
        self.assertEqual("房子", entries[0].title)
        self.assertEqual("Too Good to be True", entries[-1].title)
        self.assertEqual(list(range(1, 134)), [entry.order for entry in entries])

    def test_every_toc_entry_has_one_nonempty_article(self) -> None:
        entries = [article for part in self.book.parts for article in part.articles]
        normalized_titles = [article.key for article in entries]

        self.assertEqual(len(normalized_titles), len(set(normalized_titles)))
        self.assertTrue(all(article.paragraphs for article in entries))
        self.assertEqual(2_201, sum(len(article.paragraphs) for article in entries))
        self.assertEqual(165_948, sum(len(article.plain_text) for article in entries))

    def test_preserves_intentional_empty_paragraphs(self) -> None:
        articles = {
            article.title: article
            for part in self.book.parts
            for article in part.articles
        }

        self.assertEqual(
            2,
            sum(not paragraph.plain_text for paragraph in articles["黄金"].paragraphs),
        )

    def test_preserves_front_matter_and_normalizes_controls(self) -> None:
        self.assertEqual("序", self.book.foreword.title)
        self.assertEqual("前言", self.book.preface.title)
        self.assertIn("ISBN 978-1-9990777-0-9", self.book.colophon.plain_text)

        all_text = "\n".join(
            [
                self.book.colophon.plain_text,
                self.book.foreword.plain_text,
                self.book.preface.plain_text,
                *(article.plain_text for part in self.book.parts for article in part.articles),
            ]
        )
        self.assertNotIn("\ufeff", all_text)
        self.assertNotIn("\u2028", all_text)
        self.assertNotIn("\u2029", all_text)

    def test_renders_semantic_tex_and_escapes_reserved_characters(self) -> None:
        tex = render_content_tex(self.book)

        self.assertEqual(133, tex.count("\\BookArticle{"))
        self.assertEqual(8, tex.count("\\BookPart{"))
        self.assertIn("\\BookForeword{", tex)
        self.assertIn("\\BookPreface{", tex)
        generated_body = tex.split("\n", 1)[1]
        self.assertNotIn("%", generated_body.replace(r"\%", ""))
        self.assertIn(r"\%", generated_body)

    def test_manifest_records_reference_geometry_and_fonts(self) -> None:
        manifest = render_manifest(self.book)

        self.assertEqual({"width_pt": 432.0, "height_pt": 648.0}, manifest["page"])
        self.assertEqual(400, manifest["reference_pdf_pages"])
        self.assertEqual(133, manifest["article_count"])
        self.assertEqual(8, manifest["part_count"])
        self.assertEqual("FZNewShuSong-Z10", manifest["fonts"]["cjk_body"])
        self.assertEqual("Minion Pro", manifest["fonts"]["latin_body"])


if __name__ == "__main__":
    unittest.main()
