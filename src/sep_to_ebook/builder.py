from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .epub import build_epub
from .sep import fetch_entries


@dataclass(slots=True)
class BuildResult:
    book_title: str
    entry_count: int
    output_dir: Path
    epub_path: Path


def build_book(
    entry_urls: list[str],
    random_count: int,
    book_title: str,
    language: str,
    output_dir: Path,
    insecure: bool = False,
) -> BuildResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    book_dir = output_dir / slugify(book_title)
    html_dir = book_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    entries = fetch_entries(entry_urls=entry_urls, random_count=random_count, insecure=insecure)

    combined_parts = [
        "<html xmlns='http://www.w3.org/1999/xhtml'>",
        "<head>",
        f"<title>{escape_xml(book_title)}</title>",
        "<meta charset='utf-8'/>",
        "</head>",
        "<body>",
        f"<h1>{escape_xml(book_title)}</h1>",
    ]

    chapter_specs: list[tuple[str, str, str, bool]] = []
    for index, entry in enumerate(entries, start=1):
        chapter_name = f"{index:02d}-{entry.slug}.xhtml"
        chapter_title = entry.title
        chapter_body = entry.to_xhtml_document()
        (html_dir / chapter_name).write_text(chapter_body, encoding="utf-8")
        chapter_specs.append((chapter_name, chapter_title, chapter_body, "<math " in chapter_body))
        combined_parts.append(entry.to_xhtml_fragment())

    combined_parts.extend(["</body>", "</html>"])
    (book_dir / "book.xhtml").write_text("\n".join(combined_parts), encoding="utf-8")

    epub_path = book_dir / "book.epub"
    build_epub(
        output_path=epub_path,
        book_title=book_title,
        language=language,
        chapters=chapter_specs,
    )

    return BuildResult(
        book_title=book_title,
        entry_count=len(entries),
        output_dir=book_dir,
        epub_path=epub_path,
    )


def slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in cleaned.split("-") if part) or "book"


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
