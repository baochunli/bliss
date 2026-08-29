# 幸福 — LuaLaTeX edition

This folder is a complete, reproducible LuaLaTeX conversion of the packaged
InDesign/IDML book. It extracts the front matter and all 133 articles, orders
them from the authoritative InDesign table of contents, and applies a compact
book-specific design system in `blissbook.cls`.

The generated `book.pdf` has the reference edition's 6 x 9 inch trim size and
400-page extent. Body text uses the packaged 方正新书宋体 and Minion Pro fonts.

## Build

Requirements:

- Python 3.9 or newer
- A current TeX Live installation with LuaLaTeX, `latexmk`, CTeX, LuaTeX-ja,
  `fontspec`, `geometry`, `fancyhdr`, `multicol`, `hyperref`, and `bookmark`
- Poppler's `pdfinfo`/`pdffonts`, `qpdf`, and ripgrep (`rg`) for verification

From this directory, run:

```sh
make
```

This tests the extractor, regenerates `content/book-content.tex` and
`content/manifest.json` from `../indesign/Bliss Pages Final Edition.idml`,
compiles the book, and verifies its dimensions, page count, and build log.

Useful individual targets are `make test`, `make convert`, `make book`,
`make verify`, and `make clean`.

## Structure

- `book.tex` — minimal entry point
- `blissbook.cls` — page geometry, fonts, typography, folios, contents, section
  dividers, article openers, and front matter
- `scripts/convert_idml.py` — deterministic standard-library IDML extractor
- `tests/test_convert_idml.py` — extraction and content-integrity tests
- `content/book-content.tex` — generated semantic book content
- `content/manifest.json` — extraction audit data and original article pages
- `fonts/` — the locally packaged fonts used by this edition

`content/book-content.tex` is generated; edits to it are overwritten by
`make convert`. Put typographic changes in `blissbook.cls` and extraction
changes in `scripts/convert_idml.py`.

## Fidelity and production notes

The conversion preserves the text, article order, trim size, live area, body
fonts, heading hierarchy, two-column contents, centered folios, divider pages,
and overall 400-page extent. InDesign and LuaTeX use different line-breaking
and pagination engines, so individual article starts and blank pages can differ
from the 2019 edition. The generated table of contents always reflects the
LuaLaTeX edition.

Hiragino Sans GB W6 was named by the InDesign document but was not included in
its package. The class uses the licensed system copy when available and falls
back to Fandol Hei. SF Pro was excluded because the license shipped beside the
font prohibits embedding it in documents; TeX Gyre Heros is the Latin heading
replacement. See `FONT-NOTES.md`.

The reference PDF has no PDF/X output intent or bleed box. This build likewise
produces a standard PDF 1.7 file, not a certified PDF/X or tagged-PDF artifact.
Run the final PDF through the printer's preflight and ICC workflow before a
commercial press run.
