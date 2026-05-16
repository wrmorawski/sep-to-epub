from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def build_epub(
    output_path: Path,
    book_title: str,
    language: str,
    chapters: list[tuple[str, str, str, bool]],
) -> None:
    book_id = f"urn:uuid:{uuid4()}"
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    with ZipFile(output_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr("META-INF/container.xml", container_xml(), compress_type=ZIP_DEFLATED)
        archive.writestr("OEBPS/styles.css", stylesheet(), compress_type=ZIP_DEFLATED)
        archive.writestr("OEBPS/nav.xhtml", nav_xhtml(book_title, chapters), compress_type=ZIP_DEFLATED)
        archive.writestr("OEBPS/toc.ncx", toc_ncx(book_id, book_title, chapters), compress_type=ZIP_DEFLATED)

        for chapter_name, _, chapter_body, _ in chapters:
            archive.writestr(f"OEBPS/text/{chapter_name}", chapter_body, compress_type=ZIP_DEFLATED)

        archive.writestr(
            "OEBPS/content.opf",
            content_opf(
                book_id=book_id,
                book_title=book_title,
                language=language,
                timestamp=timestamp,
                chapters=chapters,
            ),
            compress_type=ZIP_DEFLATED,
        )


def container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def stylesheet() -> str:
    return """body { font-family: serif; line-height: 1.5; }
h1, h2, h3 { line-height: 1.2; }
section { margin-bottom: 2em; }
a { word-break: break-word; }
.math-display { margin: 1em 0; text-align: center; }
.eq-number { display: block; font-size: 0.9em; margin-top: 0.25em; }
"""


def nav_xhtml(book_title: str, chapters: list[tuple[str, str, str, bool]]) -> str:
    items = "\n".join(
        f"        <li><a href='text/{chapter_name}'>{escape_xml(chapter_title)}</a></li>"
        for chapter_name, chapter_title, _, _ in chapters
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title>{escape_xml(book_title)}</title>
    <meta charset="utf-8"/>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
  </head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>{escape_xml(book_title)}</h1>
      <ol>
{items}
      </ol>
    </nav>
  </body>
</html>
"""


def toc_ncx(book_id: str, book_title: str, chapters: list[tuple[str, str, str, bool]]) -> str:
    nav_points = "\n".join(
        f"""    <navPoint id="nav-{index}" playOrder="{index}">
      <navLabel><text>{escape_xml(chapter_title)}</text></navLabel>
      <content src="text/{chapter_name}"/>
    </navPoint>"""
        for index, (chapter_name, chapter_title, _, _) in enumerate(chapters, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{escape_xml(book_id)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{escape_xml(book_title)}</text></docTitle>
  <navMap>
{nav_points}
  </navMap>
</ncx>
"""


def content_opf(
    book_id: str,
    book_title: str,
    language: str,
    timestamp: str,
    chapters: list[tuple[str, str, str, bool]],
) -> str:
    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="css" href="styles.css" media-type="text/css"/>',
    ]
    spine_items = ['<itemref idref="nav"/>']

    for index, (chapter_name, _, _, has_mathml) in enumerate(chapters, start=1):
        item_id = f"chapter-{index}"
        properties = ' properties="mathml"' if has_mathml else ""
        manifest_items.append(
            f'<item id="{item_id}" href="text/{chapter_name}" media-type="application/xhtml+xml"{properties}/>'
        )
        spine_items.append(f'<itemref idref="{item_id}"/>')

    manifest = "\n    ".join(manifest_items)
    spine = "\n    ".join(spine_items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="2.0" unique-identifier="bookid" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{escape_xml(book_id)}</dc:identifier>
    <dc:title>{escape_xml(book_title)}</dc:title>
    <dc:language>{escape_xml(language)}</dc:language>
    <dc:creator>sep-to-ebook</dc:creator>
    <dc:date>{escape_xml(timestamp)}</dc:date>
  </metadata>
  <manifest>
    {manifest}
  </manifest>
  <spine toc="ncx">
    {spine}
  </spine>
</package>
"""


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
