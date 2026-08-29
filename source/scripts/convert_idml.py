#!/usr/bin/env python3
"""Extract the Bliss IDML book into semantic LuaLaTeX source.

The InDesign file threads article frames in a non-page-order sequence.  The
printed table of contents is therefore the authoritative ordering source;
styled article headings are used to match each TOC entry to its full text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET


ARTICLE_STYLES = {
    "Blurb Article Heading",
    "Blurb Article English Heading",
}
BODY_STYLE = "Blurb Paragraph"
DATE_STYLE = "Blurb Paragraph Date"
SUBTITLE_STYLE = "Blurb Subtitle"
FOOTNOTE_STYLES = {"Footnote", "Blurb Footnote"}
TOC_TITLE_STYLE = "Table of Contents Title"
TOC_ENTRY_STYLE = "Table of Contents Entries"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def style_name(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def normalize_controls(text: str) -> str:
    return (
        text.replace("\ufeff", "")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", "", normalize_controls(text))


def clean_title(text: str) -> str:
    return " ".join(normalize_controls(text).replace("\u3000", " ").split())


@dataclass(frozen=True)
class Span:
    text: str
    character_style: str = ""


@dataclass(frozen=True)
class Paragraph:
    style: str
    spans: Tuple[Span, ...]

    @property
    def plain_text(self) -> str:
        return "".join(span.text for span in self.spans)


@dataclass
class TextSection:
    title: str
    display_title: str
    paragraphs: List[Paragraph] = field(default_factory=list)

    @property
    def key(self) -> str:
        return normalize_key(self.title)

    @property
    def plain_text(self) -> str:
        return "\n".join(paragraph.plain_text for paragraph in self.paragraphs)


@dataclass
class Article(TextSection):
    order: int = 0
    original_page: int = 0


@dataclass
class Part:
    title: str
    articles: List[Article] = field(default_factory=list)


@dataclass
class Book:
    title: str
    author: str
    colophon: TextSection
    foreword: TextSection
    preface: TextSection
    parts: List[Part]
    page_width_pt: float
    page_height_pt: float
    reference_pdf_pages: int
    source_sha256: str


@dataclass(frozen=True)
class TocEntry:
    title: str
    page: int


@dataclass
class TocPart:
    title: str
    entries: List[TocEntry] = field(default_factory=list)


class IdmlArchive:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.archive = zipfile.ZipFile(path)

    def close(self) -> None:
        self.archive.close()

    def read_xml(self, member: str) -> ET.Element:
        return ET.fromstring(self.archive.read(member))

    def story_roots(self) -> Iterator[Tuple[str, ET.Element]]:
        for member in sorted(
            name
            for name in self.archive.namelist()
            if name.startswith("Stories/Story_") and name.endswith(".xml")
        ):
            yield member, self.read_xml(member)


def _walk_text_events(
    element: ET.Element, character_style: str = ""
) -> Iterator[Tuple[str, str, str]]:
    tag = local_name(element.tag)
    if tag == "CharacterStyleRange":
        character_style = style_name(element.get("AppliedCharacterStyle", ""))
    if tag == "Content":
        yield "text", normalize_controls(element.text or ""), character_style
        return
    if tag == "Br":
        yield "break", "", character_style
        return
    for child in element:
        yield from _walk_text_events(child, character_style)


def parse_paragraph_range(element: ET.Element) -> List[Paragraph]:
    style = style_name(element.get("AppliedParagraphStyle", ""))
    paragraph_spans: List[Tuple[Span, ...]] = []
    spans: List[Span] = []

    def flush() -> None:
        nonlocal spans
        paragraph_spans.append(tuple(spans))
        spans = []

    for event, text, character_style in _walk_text_events(element):
        if event == "break":
            flush()
        elif text:
            if spans and spans[-1].character_style == character_style:
                previous = spans[-1]
                spans[-1] = Span(previous.text + text, character_style)
            else:
                spans.append(Span(text, character_style))
    flush()

    # IDML ranges commonly carry leading/trailing <Br/> controls. They are not
    # content, but empty chunks between two nonempty paragraphs are deliberate
    # blank paragraphs and affect the book's vertical rhythm.
    while paragraph_spans and not any(span.text for span in paragraph_spans[0]):
        paragraph_spans.pop(0)
    while paragraph_spans and not any(span.text for span in paragraph_spans[-1]):
        paragraph_spans.pop()

    return [Paragraph(style=style, spans=spans) for spans in paragraph_spans]


def paragraph_ranges(root: ET.Element) -> Iterator[ET.Element]:
    for element in root.iter():
        if local_name(element.tag) == "ParagraphStyleRange":
            yield element


def plain_lines(element: ET.Element) -> List[str]:
    return [paragraph.plain_text for paragraph in parse_paragraph_range(element)]


def extract_text_sections(story_root: ET.Element) -> List[TextSection]:
    sections: List[TextSection] = []
    current: Optional[TextSection] = None

    for paragraph_range in paragraph_ranges(story_root):
        style = style_name(paragraph_range.get("AppliedParagraphStyle", ""))
        if style in ARTICLE_STYLES:
            display_title = "".join(
                text
                for text in (
                    paragraph.plain_text
                    for paragraph in parse_paragraph_range(paragraph_range)
                )
                if text.strip()
            ).strip()
            if not display_title:
                continue
            if current is not None:
                sections.append(current)
            current = TextSection(
                title=clean_title(display_title),
                display_title=display_title,
            )
            continue
        if current is not None:
            current.paragraphs.extend(parse_paragraph_range(paragraph_range))

    if current is not None:
        sections.append(current)
    return sections


def extract_toc(story_root: ET.Element) -> List[TocPart]:
    parts: List[TocPart] = []
    current: Optional[TocPart] = None

    for paragraph_range in paragraph_ranges(story_root):
        style = style_name(paragraph_range.get("AppliedParagraphStyle", ""))
        if style == TOC_TITLE_STYLE:
            for raw_title in plain_lines(paragraph_range):
                title = clean_title(raw_title)
                if not title or title == "前言":
                    continue
                current = TocPart(title=title)
                parts.append(current)
        elif style == TOC_ENTRY_STYLE:
            if current is None:
                raise ValueError("TOC entry encountered before its section title")
            for line in plain_lines(paragraph_range):
                match = re.match(r"^(.*?)[\t ]+(\d+)\s*$", line)
                if not match:
                    continue
                current.entries.append(
                    TocEntry(title=clean_title(match.group(1)), page=int(match.group(2)))
                )

    return parts


def find_story_with_style(
    stories: Sequence[Tuple[str, ET.Element]], wanted_style: str
) -> ET.Element:
    for _member, root in stories:
        if any(
            style_name(element.get("AppliedParagraphStyle", "")) == wanted_style
            for element in paragraph_ranges(root)
        ):
            return root
    raise ValueError(f"No story uses paragraph style {wanted_style!r}")


def story_plain_text(root: ET.Element) -> str:
    paragraphs: List[str] = []
    for paragraph_range in paragraph_ranges(root):
        paragraphs.extend(plain_lines(paragraph_range))
    return "\n".join(paragraphs)


def find_story_containing(
    stories: Sequence[Tuple[str, ET.Element]], needle: str
) -> ET.Element:
    for _member, root in stories:
        if needle in story_plain_text(root):
            return root
    raise ValueError(f"No story contains {needle!r}")


def page_geometry(archive: IdmlArchive) -> Tuple[float, float]:
    preferences = archive.read_xml("Resources/Preferences.xml")
    for element in preferences.iter():
        if local_name(element.tag) == "DocumentPreference":
            return float(element.get("PageWidth", "0")), float(
                element.get("PageHeight", "0")
            )
    raise ValueError("DocumentPreference not found")


def count_pages(archive: IdmlArchive) -> int:
    count = 0
    for member in archive.archive.namelist():
        if not member.startswith("Spreads/") or not member.endswith(".xml"):
            continue
        root = archive.read_xml(member)
        count += sum(1 for element in root.iter() if local_name(element.tag) == "Page")
    return count


def _copy_section(section: TextSection, title: str) -> TextSection:
    return TextSection(
        title=title,
        display_title=section.display_title,
        paragraphs=list(section.paragraphs),
    )


def extract_book(idml_path: Path) -> Book:
    idml_path = Path(idml_path)
    archive = IdmlArchive(idml_path)
    try:
        stories = list(archive.story_roots())
        toc_root = find_story_with_style(stories, TOC_ENTRY_STYLE)
        toc_parts = extract_toc(toc_root)

        sections_by_key: Dict[str, TextSection] = {}
        for _member, story_root in stories:
            for section in extract_text_sections(story_root):
                key = section.key
                if key in sections_by_key:
                    raise ValueError(f"Duplicate styled heading: {section.title!r}")
                sections_by_key[key] = section

        order = 0
        parts: List[Part] = []
        for toc_part in toc_parts:
            part = Part(title=toc_part.title)
            for entry in toc_part.entries:
                order += 1
                key = normalize_key(entry.title)
                if key not in sections_by_key:
                    raise ValueError(f"TOC article has no styled story: {entry.title!r}")
                source = sections_by_key[key]
                part.articles.append(
                    Article(
                        title=entry.title,
                        display_title=source.display_title,
                        paragraphs=list(source.paragraphs),
                        order=order,
                        original_page=entry.page,
                    )
                )
            parts.append(part)

        foreword_source = sections_by_key[normalize_key("序")]
        preface_source = sections_by_key[normalize_key("前言")]
        colophon_root = find_story_containing(stories, "ISBN 978-1-9990777-0-9")
        colophon = TextSection(
            title="版权信息",
            display_title="版权信息",
            paragraphs=[
                paragraph
                for paragraph_range in paragraph_ranges(colophon_root)
                for paragraph in parse_paragraph_range(paragraph_range)
            ],
        )
        width, height = page_geometry(archive)
        pages = count_pages(archive)
    finally:
        archive.close()

    return Book(
        title="幸福",
        author="李葆春",
        colophon=colophon,
        foreword=_copy_section(foreword_source, "序"),
        preface=_copy_section(preface_source, "前言"),
        parts=parts,
        page_width_pt=width,
        page_height_pt=height,
        reference_pdf_pages=pages,
        source_sha256=hashlib.sha256(idml_path.read_bytes()).hexdigest(),
    )


TEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "#": r"\#",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}
SYMBOL_FALLBACK_CHARACTERS = set("①②③④")


def escape_tex(text: str) -> str:
    result: List[str] = []
    for character in normalize_controls(text):
        if character in SYMBOL_FALLBACK_CHARACTERS:
            result.append(rf"{{\BlissSymbols {character}}}")
        elif character == "\n":
            result.append(r"\BookLineBreak{}")
        elif character == "\t":
            result.append(r"\BookTab{}")
        elif character == "\u00a0":
            result.append("~")
        else:
            result.append(TEX_ESCAPES.get(character, character))
    return "".join(result)


def render_span(span: Span) -> str:
    text = escape_tex(span.text)
    if span.character_style in {"English Bold", "Book Title"}:
        return rf"\textbf{{{text}}}"
    return text


def render_paragraph(paragraph: Paragraph) -> str:
    content = "".join(render_span(span) for span in paragraph.spans)
    if paragraph.style == DATE_STYLE:
        content = content.replace(r"\BookTab{}", "")
        command = "BookDate"
    elif paragraph.style == SUBTITLE_STYLE:
        content = content.replace(r"\BookTab{}", "")
        command = "BookSubtitle"
    elif paragraph.style in FOOTNOTE_STYLES:
        command = "BookFootnote"
    elif paragraph.style == BODY_STYLE:
        command = "BookParagraph"
    else:
        command = "BookPlainParagraph"
    return rf"\{command}{{{content}}}"


def vertical_tex(text: str) -> str:
    words = text.replace("\u3000", " ").split()
    vertical_words = [
        r"\\".join(escape_tex(character) for character in word) for word in words
    ]
    return r"\\[18pt]".join(vertical_words)


def render_section_paragraphs(section: TextSection) -> List[str]:
    return [render_paragraph(paragraph) for paragraph in section.paragraphs]


def render_content_tex(book: Book) -> str:
    lines = [
        "% Generated from Bliss Pages Final Edition.idml; do not edit by hand.",
        rf"\BookColophon{{{escape_tex(book.colophon.plain_text)}}}",
        rf"\BookTitlePage{{{escape_tex(book.title)}}}{{{escape_tex(book.author)}}}"
        rf"{{{vertical_tex(book.title)}}}{{{vertical_tex(book.author)}}}",
        rf"\BookForeword{{{escape_tex(book.foreword.display_title)}}}",
        *render_section_paragraphs(book.foreword),
        r"\BookTOC",
        rf"\BookPreface{{{escape_tex(book.preface.display_title)}}}",
        *render_section_paragraphs(book.preface),
    ]

    for part in book.parts:
        lines.append(
            rf"\BookPart{{{escape_tex(part.title)}}}"
            rf"{{{vertical_tex(part.title)}}}"
        )
        for article in part.articles:
            lines.append(
                rf"\BookArticle{{{escape_tex(article.display_title)}}}"
                rf"{{{escape_tex(article.title)}}}"
            )
            lines.extend(render_section_paragraphs(article))

    lines.append(r"\BookFinish")
    return "\n".join(lines) + "\n"


def render_manifest(book: Book) -> dict:
    articles = [article for part in book.parts for article in part.articles]
    return {
        "title": book.title,
        "author": book.author,
        "source_idml_sha256": book.source_sha256,
        "page": {
            "width_pt": book.page_width_pt,
            "height_pt": book.page_height_pt,
        },
        "reference_pdf_pages": book.reference_pdf_pages,
        "part_count": len(book.parts),
        "article_count": len(articles),
        "paragraph_count": sum(len(article.paragraphs) for article in articles),
        "character_count": sum(len(article.plain_text) for article in articles),
        "fonts": {
            "cjk_body": "FZNewShuSong-Z10",
            "latin_body": "Minion Pro",
            "cjk_heading": "Hiragino Sans GB (system; FandolHei fallback)",
            "latin_heading": "TeX Gyre Heros (SF Pro replacement)",
        },
        "parts": [
            {
                "title": part.title,
                "articles": [
                    {
                        "order": article.order,
                        "title": article.title,
                        "original_page": article.original_page,
                        "paragraphs": len(article.paragraphs),
                        "characters": len(article.plain_text),
                    }
                    for article in part.articles
                ],
            }
            for part in book.parts
        ],
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idml", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    book = extract_book(args.idml)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_content_tex(book), encoding="utf-8")
    args.manifest.write_text(
        json.dumps(render_manifest(book), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    article_count = sum(len(part.articles) for part in book.parts)
    print(
        f"Converted {article_count} articles in {len(book.parts)} parts "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
