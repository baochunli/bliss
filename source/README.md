# 幸福 — LuaLaTeX edition

This folder is a complete, reproducible LuaLaTeX conversion of the packaged
InDesign/IDML book, extended with the author's newer long-form writing. It
extracts the front matter and all 133 original articles, orders them from the
authoritative InDesign table of contents, appends 89 newer articles from the
author's personal website, and applies a compact book-specific design system in
`blissbook.cls`.

The generated `book.pdf` has the reference edition's 6 x 9 inch trim size. Body
text uses the packaged 方正新书宋体 and Minion Pro fonts.

## Build

Requirements:

- Python 3.9 or newer
- A current TeX Live installation with LuaLaTeX, `latexmk`, CTeX, LuaTeX-ja,
  `fontspec`, `geometry`, `fancyhdr`, `graphicx`, `multicol`, `hyperref`, and
  `bookmark`
- Poppler's `pdfinfo`/`pdffonts`, `qpdf`, and ripgrep (`rg`) for verification

From this directory, run:

```sh
make
```

This tests the extractors, regenerates `content/book-content.tex` and
`content/manifest.json` from `../indesign/Bliss Pages Final Edition.idml` and
`articles/`, compiles the book, and verifies its dimensions, page parity, font
embedding, PDF structure, and build log.

Useful individual targets are `make test`, `make convert`, `make book`,
`make verify`, and `make clean`.

## Structure

- `book.tex` — minimal entry point
- `blissbook.cls` — page geometry, fonts, typography, folios, contents, section
  dividers, article openers, and front matter
- `scripts/convert_idml.py` — deterministic standard-library IDML and Markdown
  extractor
- `tests/` — extraction, selection, conversion, and content-integrity tests
- `articles/` — vendored R Markdown for the 89 newer articles
- `images/` — the three local images referenced by those articles
- `content/book-content.tex` — generated semantic book content
- `content/manifest.json` — extraction audit data, original article pages, and
  website source provenance and hashes
- `fonts/` — the locally packaged fonts used by this edition

`content/book-content.tex` is generated; edits to it are overwritten by
`make convert`. Put typographic changes in `blissbook.cls` and extraction
changes in `scripts/convert_idml.py`.

## Website article selection

The newer articles are the category 01–08 entries that follow the final
article in each original-book category, using the website's numeric `weight`
as the stable boundary and order. The importer explicitly excludes category 09
`昙花一现` (short, dated Weibo entries), category 10 `他山之石` (external
articles), and the website foreword already present in the IDML. It does not
deduplicate titles: both articles named `相亲` are intentional.

The selected `.Rmd` files and referenced images are vendored here so a build
does not depend on a neighboring website checkout. `content/manifest.json`
records each website filename and SHA-256 digest for provenance.

## Fidelity and production notes

The conversion preserves the text, article order, trim size, live area, body
fonts, heading hierarchy, two-column contents, outside folios, divider pages,
and the original design system. The 89 additional articles necessarily extend
the book beyond the original 400 pages. InDesign and LuaTeX use different
line-breaking and pagination engines, so individual article starts and blank
pages can differ from the 2019 edition. The generated table of contents always
reflects the LuaLaTeX edition.

The source contains one crying-face emoji that is unavailable in the packaged
fonts. The class renders it with an explicit textual fallback rather than
silently depending on a system emoji font.

Hiragino Sans GB W6 was named by the InDesign document but was not included in
its package. The class uses the licensed system copy when available and falls
back to Fandol Hei. SF Pro Display Bold is not used because its license forbids
this kind of document use; TeX Gyre Heros is the licensed Latin heading
replacement. See `FONT-NOTES.md`.

The reference PDF has no PDF/X output intent or bleed box. This build likewise
produces a standard PDF 1.7 file, not a certified PDF/X or tagged-PDF artifact.
Run the final PDF through the printer's preflight and ICC workflow before a
commercial press run.
