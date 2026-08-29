# Font notes

The `fonts/` directory contains local copies of fonts found in the InDesign
package and used by this LuaLaTeX edition:

- `FZNewShuSong-Z10.ttf` — Chinese body text
- `MinionPro-Regular.otf` and `MinionPro-Bold.otf` — Latin body text
- `AdobeSongStd-Light.otf` — fallback for circled-number glyphs

`FZNewShuSong-Z10S.ttf` is used for the title-page byline, matching its special
use in the InDesign edition.

Hiragino Sans GB W6 is loaded from the operating system when installed because
it was referenced by InDesign but not packaged. TeX Live's Fandol Hei is the
portable fallback.

The packaged SF Pro font is deliberately not copied here. Its accompanying
license says it may not be embedded in documents. TeX Gyre Heros, distributed
with TeX Live, replaces it for Latin headings. A publisher with separate SF Pro
embedding rights can change `\BlissHeadingLatin` in `blissbook.cls`.

These font files remain subject to their original licenses. Keeping them in
this working source folder does not grant redistribution rights.
