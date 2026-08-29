from __future__ import annotations

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SOURCE_DIR.parent
INDESIGN_DIR = PROJECT_DIR / "indesign"
ARTICLES_DIR = SOURCE_DIR / "articles"
sys.path.insert(0, str(SOURCE_DIR / "scripts"))

from convert_idml import (  # noqa: E402
    append_website_articles,
    extract_book,
    extract_website_articles,
    render_content_tex,
    render_manifest,
)


class ImportWebsiteArticlesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.website_articles = extract_website_articles(ARTICLES_DIR)
        cls.book = append_website_articles(
            extract_book(INDESIGN_DIR / "Bliss Pages Final Edition.idml"),
            cls.website_articles,
        )

    def test_selects_all_new_authored_articles_in_weight_order(self) -> None:
        expected_counts = {
            "幸福": 9,
            "将爱情进行到底": 9,
            "芳华已逝 面目全非": 5,
            "好好学习 天天向上": 23,
            "长期共存 互相吹捧": 2,
            "为祖国健康工作五十年": 25,
            "儿孙自有儿孙福": 2,
            "柴米油盐酱醋茶": 14,
        }

        self.assertEqual(89, len(self.website_articles))
        self.assertEqual(
            expected_counts,
            Counter(article.category for article in self.website_articles),
        )
        self.assertEqual(
            sorted(
                self.website_articles,
                key=lambda article: (article.category_order, article.weight),
            ),
            self.website_articles,
        )
        self.assertTrue(all(article.year for article in self.website_articles))
        self.assertEqual(
            {
                "Blurb Paragraph": 1_193,
                "Website Quote": 118,
                "Blurb Paragraph Date": 90,
                "Blurb Subtitle": 86,
                "Blurb Footnote": 3,
                "Website Image": 3,
                "Website Left": 2,
            },
            Counter(
                paragraph.style
                for article in self.website_articles
                for paragraph in article.paragraphs
            ),
        )

    def test_uses_weight_cutoffs_and_keeps_new_duplicate_title(self) -> None:
        imported_weights = {
            (article.category_order, article.weight)
            for article in self.website_articles
        }

        self.assertIn((1, 17), imported_weights)
        self.assertIn((2, 1026), imported_weights)
        self.assertIn((8, 7038), imported_weights)
        self.assertNotIn((1, 16), imported_weights)
        self.assertEqual(
            2,
            sum(
                article.title == "相亲"
                for part in self.book.parts
                for article in part.articles
            ),
        )

    def test_excludes_weibo_external_articles_and_existing_foreword(self) -> None:
        source_names = {article.source_path for article in self.website_articles}

        self.assertFalse(any(name.startswith("weibo-") for name in source_names))
        self.assertNotIn("beida.Rmd", source_names)
        self.assertNotIn("paper-writing.Rmd", source_names)
        self.assertNotIn("intro.Rmd", source_names)

    def test_renders_supported_markdown_without_source_markup_leaks(self) -> None:
        tex = render_content_tex(self.book)

        self.assertEqual(222, tex.count("\\BookArticle{"))
        self.assertEqual(3, tex.count("\\BookImage{"))
        self.assertEqual(4, tex.count("\\footnote{"))
        self.assertEqual(5, tex.count("\\href{https://baochun.ca/"))
        self.assertIn("\\BookQuote{", tex)
        self.assertIn("\\BookSubtitle{", tex)
        self.assertIn("\\BlissCJKFallback", tex)
        self.assertNotIn("\\href{/", tex)
        self.assertNotIn("\u2003", tex)
        self.assertNotIn("#####", tex)
        self.assertNotIn("<div", tex)
        self.assertNotIn("[^", tex)
        self.assertNotIn("😭", tex)

    def test_manifest_audits_every_website_source(self) -> None:
        manifest = render_manifest(self.book)
        website_sources = [
            article
            for part in manifest["parts"]
            for article in part["articles"]
            if article["source"] == "website"
        ]

        self.assertEqual(222, manifest["article_count"])
        self.assertEqual(89, manifest["website_article_count"])
        self.assertEqual(3_696, manifest["paragraph_count"])
        self.assertEqual(279_954, manifest["character_count"])
        self.assertEqual(89, len(website_sources))
        self.assertTrue(all(article["source_sha256"] for article in website_sources))
        self.assertEqual(
            {
                "images/childrens-day.jpg",
                "images/google-sheets.png",
                "images/weibo-5276734135997229-1-2b232b7a4f.jpg",
            },
            {asset["path"] for asset in manifest["website_assets"]},
        )
        self.assertTrue(
            all(asset["sha256"] for asset in manifest["website_assets"])
        )

    def test_rejects_unsupported_markdown_with_source_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            article_dir = Path(directory) / "articles"
            article_dir.mkdir()
            (article_dir / "unsupported.Rmd").write_text(
                """---
title: Unsupported
weight: 17
slug: 幸福/unsupported
目录:
  - 01幸福
标签:
  - 2026年
---

```python
print('unsupported')
```
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, r"unsupported\.Rmd:\d+: unsupported fenced code block"
            ):
                extract_website_articles(article_dir)

    def test_rejects_missing_images_with_source_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            article_dir = Path(directory) / "articles"
            article_dir.mkdir()
            (article_dir / "missing-image.Rmd").write_text(
                """---
title: Missing image
weight: 17
目录:
  - 01幸福
标签:
  - 2026年
---

<div align=center>![missing](/images/missing.png){width=70%}</div>
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, r"missing-image\.Rmd:\d+: missing image"
            ):
                extract_website_articles(article_dir)


if __name__ == "__main__":
    unittest.main()
