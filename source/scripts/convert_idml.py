#!/usr/bin/env python3
"""Extract the Bliss IDML book into semantic LuaLaTeX source.

The InDesign file threads article frames in a non-page-order sequence.  The
printed table of contents is therefore the authoritative ordering source;
styled article headings are used to match each TOC entry to its full text.
"""

from __future__ import annotations

import argparse
import hashlib
import html
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
WEBSITE_QUOTE_STYLE = "Website Quote"
WEBSITE_QUESTION_STYLE = "Website Question"
WEBSITE_IMAGE_STYLE = "Website Image"
WEBSITE_LEFT_STYLE = "Website Left"
WEBSITE_BASE_URL = "https://baochun.ca"

WEBSITE_PARTS = {
    "01幸福": (1, "幸福", 17),
    "02将爱情进行到底": (2, "将爱情进行到底", 1026),
    "03芳华已逝面目全非": (3, "芳华已逝 面目全非", 2009),
    "04好好学习天天向上": (4, "好好学习 天天向上", 3021),
    "05长期共存互相吹捧": (5, "长期共存 互相吹捧", 4007),
    "06为祖国健康工作五十年": (6, "为祖国健康工作五十年", 5020),
    "07儿孙自有儿孙福": (7, "儿孙自有儿孙福", 6007),
    "08柴米油盐酱醋茶": (8, "柴米油盐酱醋茶", 7025),
}


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


def website_display_title(title: str) -> str:
    if len(title) == 2 and all(
        "\u3400" <= character <= "\u9fff" for character in title
    ):
        return "\u3000".join(title)
    return title


@dataclass(frozen=True)
class Span:
    text: str
    character_style: str = ""
    target: str = ""


@dataclass(frozen=True)
class Paragraph:
    style: str
    spans: Tuple[Span, ...]
    attributes: Tuple[Tuple[str, str], ...] = ()

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
    category: str = ""
    category_order: int = 0
    weight: int = 0
    year: str = ""
    source_kind: str = "idml"
    source_path: str = ""
    source_sha256: str = ""


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


def _front_matter_scalar(front_matter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", front_matter)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def _front_matter_list_item(front_matter: str, key: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(key)}:\s*\n\s*-\s*(.*?)\s*$", front_matter
    )
    return match.group(1).strip() if match else ""


def _split_rmd(path: Path) -> Tuple[str, List[Tuple[int, str]]]:
    lines = normalize_controls(path.read_text(encoding="utf-8")).split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path.name}:1: missing YAML front matter")
    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line == "---"
        )
    except StopIteration as error:
        raise ValueError(f"{path.name}:1: unterminated YAML front matter") from error
    front_matter = "\n".join(lines[1:closing_index])
    body = list(enumerate(lines[closing_index + 1 :], start=closing_index + 2))
    return front_matter, body


def _extract_footnotes(
    lines: Sequence[Tuple[int, str]], path: Path
) -> Tuple[List[Tuple[int, str]], Dict[str, str]]:
    body: List[Tuple[int, str]] = []
    footnotes: Dict[str, str] = {}
    index = 0
    while index < len(lines):
        line_number, line = lines[index]
        match = re.match(r"^\[\^([^]]+)\]:\s*(.*)$", line)
        if not match:
            body.append((line_number, line))
            index += 1
            continue

        name, first_line = match.groups()
        if name in footnotes:
            raise ValueError(f"{path.name}:{line_number}: duplicate footnote {name!r}")
        chunks = [first_line.strip()]
        index += 1
        while index < len(lines):
            _continuation_number, continuation = lines[index]
            if continuation.startswith("    "):
                chunks.append(continuation.strip())
                index += 1
                continue
            if (
                not continuation.strip()
                and index + 1 < len(lines)
                and lines[index + 1][1].startswith("    ")
            ):
                index += 1
                continue
            break
        footnotes[name] = " ".join(chunk for chunk in chunks if chunk)
    return body, footnotes


def _append_span(spans: List[Span], span: Span) -> None:
    if not span.text:
        return
    if (
        spans
        and spans[-1].character_style == span.character_style
        and spans[-1].target == span.target
    ):
        previous = spans[-1]
        spans[-1] = Span(previous.text + span.text, span.character_style, span.target)
    else:
        spans.append(span)


INLINE_MARKDOWN = re.compile(
    r"(<br\s*/?>|<sup>.*?</sup>|\*\*.*?\*\*|`[^`]*`|"
    r"\[\^[^]]+\]|(?<!!)\[[^]]+\]\([^)]+\))",
    re.IGNORECASE,
)


def parse_markdown_inline(
    text: str,
    footnotes: Dict[str, str],
    path: Path,
    line_number: int,
) -> Tuple[Span, ...]:
    text = re.sub(r"</?span(?:\s+[^>]*)?>", "", text, flags=re.IGNORECASE)
    if re.search(r"</?(?:div|img|p|table|ul|ol|li)\b", text, re.IGNORECASE):
        raise ValueError(f"{path.name}:{line_number}: unsupported inline HTML")
    if "![" in text:
        raise ValueError(f"{path.name}:{line_number}: inline image must be centered")

    text = html.unescape(text)
    spans: List[Span] = []
    position = 0
    for match in INLINE_MARKDOWN.finditer(text):
        _append_span(spans, Span(text[position : match.start()]))
        token = match.group(0)
        if re.fullmatch(r"<br\s*/?>", token, re.IGNORECASE):
            _append_span(spans, Span("\n"))
        elif token.startswith("<sup>"):
            _append_span(spans, Span(token[5:-6], "Markdown Superscript"))
        elif token.startswith("**"):
            _append_span(spans, Span(token[2:-2], "Markdown Bold"))
        elif token.startswith("`"):
            _append_span(spans, Span(token[1:-1], "Markdown Code"))
        elif token.startswith("[^"):
            name = token[2:-1]
            if name not in footnotes:
                raise ValueError(
                    f"{path.name}:{line_number}: undefined footnote {name!r}"
                )
            _append_span(spans, Span(footnotes[name], "Markdown Footnote"))
        else:
            link = re.fullmatch(r"\[([^]]+)\]\(([^)]+)\)", token)
            if link is None:
                raise AssertionError(f"Unrecognized inline token: {token}")
            _append_span(spans, Span(link.group(1), "Markdown Link", link.group(2)))
        position = match.end()
    _append_span(spans, Span(text[position:]))
    return tuple(spans)


def _join_markdown_lines(lines: Sequence[str]) -> str:
    result = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        separator = ""
        if result and result[-1].isascii() and stripped[0].isascii():
            if result[-1].isalnum() and stripped[0].isalnum():
                separator = " "
        result += separator + stripped
    return result


def _paragraph(
    style: str,
    text: str,
    footnotes: Dict[str, str],
    path: Path,
    line_number: int,
    attributes: Tuple[Tuple[str, str], ...] = (),
) -> Paragraph:
    return Paragraph(
        style=style,
        spans=parse_markdown_inline(text, footnotes, path, line_number),
        attributes=attributes,
    )


def _parse_markdown_blocks(
    lines: Sequence[Tuple[int, str]], path: Path, article_dir: Path
) -> List[Paragraph]:
    lines, footnotes = _extract_footnotes(lines, path)
    paragraphs: List[Paragraph] = []
    index = 0

    while index < len(lines):
        line_number, line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            raise ValueError(
                f"{path.name}:{line_number}: unsupported fenced code block"
            )
        if re.match(r"^\s*(?:[-*+] |\d+[.)] )", line):
            raise ValueError(f"{path.name}:{line_number}: unsupported Markdown list")
        if re.match(r"^\s*\|.*\|\s*$", line):
            raise ValueError(f"{path.name}:{line_number}: unsupported Markdown table")

        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            paragraphs.append(
                _paragraph(
                    SUBTITLE_STYLE,
                    heading.group(1),
                    footnotes,
                    path,
                    line_number,
                )
            )
            index += 1
            continue

        if stripped.startswith(">"):
            quote_lines: List[Tuple[int, str]] = []
            while index < len(lines) and lines[index][1].strip().startswith(">"):
                quote_number, quote_line = lines[index]
                quote_lines.append(
                    (quote_number, re.sub(r"^\s*>\s?", "", quote_line))
                )
                index += 1
            current: List[str] = []
            current_line = quote_lines[0][0]
            for quote_number, quote_line in quote_lines + [(0, "")]:
                if quote_line.strip():
                    if not current:
                        current_line = quote_number
                    current.append(quote_line)
                elif current:
                    paragraphs.append(
                        _paragraph(
                            WEBSITE_QUOTE_STYLE,
                            _join_markdown_lines(current),
                            footnotes,
                            path,
                            current_line,
                        )
                    )
                    current = []
            continue

        if re.fullmatch(r"<div>\s*(?:&nbsp;)?\s*</div>", stripped, re.IGNORECASE):
            index += 1
            continue

        center_image = re.fullmatch(
            r"<div\s+align=center>\s*!\[([^]]*)\]\(([^)]+)\)"
            r"\{\s*width=(\d+)%\s*\}\s*</div>",
            stripped,
            re.IGNORECASE,
        )
        if center_image:
            alt, source_path, width_percent = center_image.groups()
            local_path = "images/" + Path(source_path).name
            asset_path = article_dir.parent / local_path
            if not asset_path.is_file():
                raise ValueError(
                    f"{path.name}:{line_number}: missing image {source_path!r}"
                )
            paragraphs.append(
                _paragraph(
                    WEBSITE_IMAGE_STYLE,
                    alt,
                    footnotes,
                    path,
                    line_number,
                    attributes=(
                        ("path", local_path),
                        (
                            "sha256",
                            hashlib.sha256(asset_path.read_bytes()).hexdigest(),
                        ),
                        ("width", str(int(width_percent) / 100)),
                    ),
                )
            )
            index += 1
            continue

        inline_div = re.fullmatch(
            r"<div\s+align=(right|left)>\s*(.*?)\s*</div>",
            stripped,
            re.IGNORECASE,
        )
        if inline_div:
            alignment, text = inline_div.groups()
            if text:
                paragraphs.append(
                    _paragraph(
                        DATE_STYLE
                        if alignment.lower() == "right"
                        else WEBSITE_LEFT_STYLE,
                        text,
                        footnotes,
                        path,
                        line_number,
                    )
                )
            index += 1
            continue

        div_match = re.fullmatch(r"<div\s+align=(right|left)>", stripped, re.I)
        if div_match:
            alignment = div_match.group(1).lower()
            div_lines: List[str] = []
            index += 1
            while index < len(lines) and lines[index][1].strip() != "</div>":
                div_lines.append(lines[index][1])
                index += 1
            if index >= len(lines):
                raise ValueError(f"{path.name}:{line_number}: unterminated div")
            text = _join_markdown_lines(div_lines)
            if text:
                paragraphs.append(
                    _paragraph(
                        DATE_STYLE if alignment == "right" else WEBSITE_LEFT_STYLE,
                        text,
                        footnotes,
                        path,
                        line_number,
                    )
                )
            index += 1
            continue

        if stripped.startswith("<div") or stripped == "</div>":
            raise ValueError(f"{path.name}:{line_number}: unsupported div")

        ordinary_lines = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index][1]
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                break
            if (
                candidate_stripped.startswith((">", "#", "<div", "```"))
                or re.match(r"^\s*(?:[-*+] |\d+[.)] )", candidate)
            ):
                break
            ordinary_lines.append(candidate)
            index += 1
        paragraph_style = (
            "Blurb Footnote"
            if ordinary_lines[0].lstrip().startswith(tuple("①②③④"))
            else BODY_STYLE
        )
        paragraphs.append(
            _paragraph(
                paragraph_style,
                _join_markdown_lines(ordinary_lines),
                footnotes,
                path,
                line_number,
            )
        )

    return paragraphs


def _classify_leading_website_questions(
    paragraphs: Sequence[Paragraph],
) -> List[Paragraph]:
    """Give an article's leading blockquote run reader-question semantics."""
    classified = list(paragraphs)
    for index, paragraph in enumerate(classified):
        if paragraph.style != WEBSITE_QUOTE_STYLE:
            break
        classified[index] = Paragraph(
            style=WEBSITE_QUESTION_STYLE,
            spans=paragraph.spans,
            attributes=paragraph.attributes,
        )
    return classified


def extract_website_articles(article_dir: Path) -> List[Article]:
    article_dir = Path(article_dir)
    if not article_dir.is_dir():
        raise ValueError(f"Website article directory not found: {article_dir}")

    articles: List[Article] = []
    for path in sorted(article_dir.glob("*.Rmd")):
        front_matter, body_lines = _split_rmd(path)
        category_key = _front_matter_list_item(front_matter, "目录")
        if category_key not in WEBSITE_PARTS:
            continue
        category_order, category, cutoff = WEBSITE_PARTS[category_key]
        weight_text = _front_matter_scalar(front_matter, "weight")
        if not weight_text.isdigit():
            raise ValueError(f"{path.name}:1: missing numeric weight")
        weight = int(weight_text)
        if weight < cutoff:
            continue
        title = _front_matter_scalar(front_matter, "title")
        year = _front_matter_list_item(front_matter, "标签")
        if not title or not year:
            raise ValueError(f"{path.name}:1: missing title or year")
        paragraphs = _classify_leading_website_questions(
            _parse_markdown_blocks(body_lines, path, article_dir)
        )
        if not paragraphs:
            raise ValueError(f"{path.name}: empty article")
        articles.append(
            Article(
                title=title,
                display_title=website_display_title(title),
                paragraphs=paragraphs,
                category=category,
                category_order=category_order,
                weight=weight,
                year=year,
                source_kind="website",
                source_path=path.name,
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )

    articles.sort(key=lambda article: (article.category_order, article.weight))
    keys = [(article.category_order, article.weight) for article in articles]
    if len(keys) != len(set(keys)):
        raise ValueError("Website article category/weight values must be unique")
    return articles


def append_website_articles(book: Book, articles: Sequence[Article]) -> Book:
    if any(
        article.source_kind == "website"
        for part in book.parts
        for article in part.articles
    ):
        raise ValueError("Book already contains website articles")
    part_by_title = {part.title: part for part in book.parts}
    for article in sorted(
        articles, key=lambda item: (item.category_order, item.weight)
    ):
        if article.category not in part_by_title:
            raise ValueError(f"No book part matches {article.category!r}")
        part_by_title[article.category].articles.append(article)

    order = 0
    for part in book.parts:
        for article in part.articles:
            order += 1
            article.order = order
    return book


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
CJK_FALLBACK_CHARACTERS = set("ǎǔ")
CJK_CLOSING_PUNCTUATION = set("》」』】）〕］〉”’")
CJK_FOLLOWING_PUNCTUATION = set("，。；：！？、")
CJK_EM_DASH_BOUNDARIES = set("「」『』《》〈〉【】〔〕（）［］，。；：！？、")


def website_latin_quote_indices(text: str) -> set[int]:
    indices: set[int] = set()
    search_from = 0
    while True:
        opener = text.find("“", search_from)
        if opener < 0:
            return indices

        terminators = [
            index
            for index in (text.find("”", opener + 1), text.find('"', opener + 1))
            if index >= 0
        ]
        if not terminators:
            return indices

        closer = min(terminators)
        quoted = text[opener + 1 : closer]
        has_latin = any(character.isascii() and character.isalpha() for character in quoted)
        has_han = any("\u3400" <= character <= "\u9fff" for character in quoted)
        if has_latin and not has_han:
            indices.add(opener)
            if text[closer] == "”":
                indices.add(closer)
        search_from = closer + 1


def english_em_dash_indices(text: str) -> Tuple[set[int], set[int]]:
    """Find em-dash runs between English words.

    Chinese typography conventionally uses two adjacent em-dash characters.
    Source text sometimes carries that convention into English prose.  A
    qualifying run is rendered as one Latin em dash; remaining codepoints in
    the run are suppressed.  CJK brackets and Han characters stop the local
    context scan so Chinese parenthetical dashes are preserved.
    """
    normalized = normalize_controls(text)
    replacements: set[int] = set()
    suppressed: set[int] = set()
    has_latin = any(
        character.isascii() and character.isalpha() for character in normalized
    )
    has_han = any("\u3400" <= character <= "\u9fff" for character in normalized)

    def nearest_alphanumeric(index: int, step: int) -> Optional[str]:
        while 0 <= index < len(normalized):
            character = normalized[index]
            if (
                character in CJK_EM_DASH_BOUNDARIES
                or "\u3400" <= character <= "\u9fff"
            ):
                return None
            if character.isalnum():
                return character
            index += step
        return None

    for match in re.finditer(r"—+", normalized):
        left = nearest_alphanumeric(match.start() - 1, -1)
        right = nearest_alphanumeric(match.end(), 1)
        between_english_words = bool(
            left
            and right
            and left.isascii()
            and left.isalpha()
            and right.isascii()
            and right.isalpha()
        )
        if (has_latin and not has_han) or between_english_words:
            replacements.add(match.start())
            suppressed.update(range(match.start() + 1, match.end()))
    return replacements, suppressed


def escape_tex(
    text: str,
    latin_quote_indices: Optional[set[int]] = None,
    latin_em_dash_indices: Optional[set[int]] = None,
    suppressed_em_dash_indices: Optional[set[int]] = None,
) -> str:
    result: List[str] = []
    normalized = normalize_controls(text)
    latin_quote_indices = latin_quote_indices or set()
    latin_em_dash_indices = latin_em_dash_indices or set()
    suppressed_em_dash_indices = suppressed_em_dash_indices or set()
    for index, character in enumerate(normalized):
        if index in suppressed_em_dash_indices:
            continue
        if (
            index > 0
            and normalized[index - 1] in CJK_CLOSING_PUNCTUATION
            and character in CJK_FOLLOWING_PUNCTUATION
        ):
            result.append(r"\CJKPunctuationPairGap{}")

        if character == "“" and index in latin_quote_indices:
            result.append(r"\LatinLeftDoubleQuote{}")
        elif character == "”" and index in latin_quote_indices:
            result.append(r"\LatinRightDoubleQuote{}")
        elif character == "’":
            result.append(r"\LatinApostrophe{}")
        elif character == "—" and index in latin_em_dash_indices:
            result.append(r"\LatinEmDash{}")
        elif character == "・":
            result.append("·")
        elif character in SYMBOL_FALLBACK_CHARACTERS:
            result.append(rf"{{\BlissSymbols {character}}}")
        elif character in CJK_FALLBACK_CHARACTERS:
            result.append(rf"{{\BlissCJKFallback {character}}}")
        elif character == "\u2003":
            result.append(r"\hspace{1em}")
        elif character == "😭":
            result.append(r"\BlissCryingEmoji{}")
        elif character == "\n":
            result.append(r"\BookLineBreak{}")
        elif character == "\t":
            result.append(r"\BookTab{}")
        elif character == "\u00a0":
            result.append("~")
        else:
            result.append(TEX_ESCAPES.get(character, character))
    return "".join(result)


def escape_tex_url(url: str) -> str:
    url = re.sub(r"\s+", "", url)
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = WEBSITE_BASE_URL + url
    replacements = {
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "&": r"\&",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in url)


def render_span(
    span: Span,
    latin_quote_indices: Optional[set[int]] = None,
    infer_website_smart_quotes: bool = False,
    latin_em_dash_indices: Optional[set[int]] = None,
    suppressed_em_dash_indices: Optional[set[int]] = None,
) -> str:
    quote_indices = set(latin_quote_indices or ())
    if span.character_style == "Apostrophe":
        quote_indices.update(
            index
            for index, character in enumerate(normalize_controls(span.text))
            if character in "“”"
        )
    text = escape_tex(
        span.text,
        quote_indices,
        latin_em_dash_indices,
        suppressed_em_dash_indices,
    )
    if span.character_style in {"English Bold", "Book Title", "Markdown Bold"}:
        return rf"\textbf{{{text}}}"
    if span.character_style == "Markdown Code":
        return rf"\texttt{{{text}}}"
    if span.character_style == "Markdown Superscript":
        return rf"\textsuperscript{{{text}}}"
    if span.character_style == "Markdown Link":
        return rf"\href{{{escape_tex_url(span.target)}}}{{{text}}}"
    if span.character_style == "Markdown Footnote":
        note_spans = parse_markdown_inline(
            span.text, {}, Path("footnote"), 0
        )
        note = render_spans(note_spans, infer_website_smart_quotes)
        return rf"\footnote{{{note}}}"
    return text


def render_spans(
    spans: Sequence[Span], infer_website_smart_quotes: bool = False
) -> str:
    rendered: List[str] = []
    normalized_spans = [normalize_controls(span.text) for span in spans]
    latin_quote_indices = (
        website_latin_quote_indices("".join(normalized_spans))
        if infer_website_smart_quotes
        else set()
    )
    latin_em_dash_indices, suppressed_em_dash_indices = english_em_dash_indices(
        "".join(normalized_spans)
    )
    previous_character = ""
    offset = 0
    for span, normalized in zip(spans, normalized_spans):
        if (
            previous_character in CJK_CLOSING_PUNCTUATION
            and normalized
            and normalized[0] in CJK_FOLLOWING_PUNCTUATION
        ):
            rendered.append(r"\CJKPunctuationPairGap{}")
        local_quote_indices = {
            index - offset
            for index in latin_quote_indices
            if offset <= index < offset + len(normalized)
        }
        local_em_dash_indices = {
            index - offset
            for index in latin_em_dash_indices
            if offset <= index < offset + len(normalized)
        }
        local_suppressed_em_dash_indices = {
            index - offset
            for index in suppressed_em_dash_indices
            if offset <= index < offset + len(normalized)
        }
        rendered.append(
            render_span(
                span,
                local_quote_indices,
                infer_website_smart_quotes,
                local_em_dash_indices,
                local_suppressed_em_dash_indices,
            )
        )
        if normalized:
            previous_character = normalized[-1]
        offset += len(normalized)
    return "".join(rendered)


def render_paragraph(
    paragraph: Paragraph, infer_website_smart_quotes: bool = False
) -> str:
    content = render_spans(paragraph.spans, infer_website_smart_quotes)
    attributes = dict(paragraph.attributes)
    if paragraph.style == WEBSITE_IMAGE_STYLE:
        return (
            rf"\BookImage{{{escape_tex(attributes['path'])}}}"
            rf"{{{attributes['width']}}}{{{content}}}"
        )
    if paragraph.style == WEBSITE_QUESTION_STYLE:
        command = "BookQuestion"
    elif paragraph.style == WEBSITE_QUOTE_STYLE:
        command = "BookQuote"
    elif paragraph.style == WEBSITE_LEFT_STYLE:
        command = "BookLeftParagraph"
    elif paragraph.style == DATE_STYLE:
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
    infer_website_smart_quotes = getattr(section, "source_kind", "") == "website"
    return [
        render_paragraph(paragraph, infer_website_smart_quotes)
        for paragraph in section.paragraphs
    ]


def render_colophon(section: TextSection) -> str:
    lines: List[str] = []
    reached_unlabelled_lines = False

    for paragraph in section.paragraphs:
        text = paragraph.plain_text.rstrip()
        fields = text.split("\t")

        if len(fields) == 2 and all(fields):
            if reached_unlabelled_lines:
                raise ValueError("Labelled colophon row follows unlabelled text")
            label, value = fields
            value_tex = escape_tex(value).replace('"', r"\TextQuote{}")
            value_tex = value_tex.replace("×", r"\CJKTimes{}")
            value_tex = value_tex.replace("–", r"\LatinDash{}")
            lines.append(
                rf"\BookColophonRow{{{escape_tex(label)}}}{{{value_tex}}}"
            )
        elif len(fields) == 3 and not fields[0] and not fields[1] and fields[2]:
            if reached_unlabelled_lines:
                raise ValueError("Colophon continuation follows unlabelled text")
            lines.append(
                rf"\BookColophonContinuation{{{escape_tex(fields[2])}}}"
            )
        elif len(fields) == 1 and fields[0]:
            if not reached_unlabelled_lines:
                lines.append(r"\BookColophonGap{}")
                reached_unlabelled_lines = True
            lines.append(rf"\BookColophonText{{{escape_tex(fields[0])}}}")
        else:
            raise ValueError(f"Unsupported colophon row: {text!r}")

    return "\n".join(lines)


def render_content_tex(book: Book) -> str:
    website_count = sum(
        article.source_kind == "website"
        for part in book.parts
        for article in part.articles
    )
    generated_from = "Bliss Pages Final Edition.idml"
    if website_count:
        generated_from += f" and {website_count} website articles"
    lines = [
        f"% Generated from {generated_from}; do not edit by hand.",
        "\\BookColophon{\n" + render_colophon(book.colophon) + "\n}",
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
    website_assets: Dict[str, str] = {}
    for article in articles:
        for paragraph in article.paragraphs:
            if paragraph.style != WEBSITE_IMAGE_STYLE:
                continue
            attributes = dict(paragraph.attributes)
            website_assets[attributes["path"]] = attributes["sha256"]
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
        "website_article_count": sum(
            article.source_kind == "website" for article in articles
        ),
        "paragraph_count": sum(len(article.paragraphs) for article in articles),
        "character_count": sum(len(article.plain_text) for article in articles),
        "website_assets": [
            {"path": path, "sha256": sha256}
            for path, sha256 in sorted(website_assets.items())
        ],
        "fonts": {
            "cjk_body": "FZNewShuSong-Z10",
            "latin_body": "Minion Pro",
            "cjk_heading": "Hiragino Sans GB (system; FandolHei fallback)",
            "latin_heading": "SF Pro Display Bold (packaged)",
        },
        "parts": [
            {
                "title": part.title,
                "articles": [
                    {
                        "order": article.order,
                        "title": article.title,
                        "source": article.source_kind,
                        "source_path": article.source_path,
                        "source_sha256": article.source_sha256,
                        "weight": article.weight,
                        "year": article.year,
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
    parser.add_argument("--articles", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    book = extract_book(args.idml)
    if args.articles:
        append_website_articles(book, extract_website_articles(args.articles))
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
