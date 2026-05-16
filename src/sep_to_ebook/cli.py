from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_book


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Stanford Encyclopedia of Philosophy entries and package them as EPUB."
    )
    parser.add_argument(
        "--entry-url",
        dest="entry_urls",
        action="append",
        default=[],
        help="Explicit SEP entry URL. Repeat to include multiple entries.",
    )
    parser.add_argument(
        "--random-count",
        type=int,
        default=0,
        help="Number of random SEP entries to fetch from the SEP random-entry endpoint.",
    )
    parser.add_argument(
        "--book-title",
        required=True,
        help="Title for the generated book.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="EPUB language code. Defaults to en.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated HTML and EPUB files.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for SEP fetches. Use only if your local network intercepts HTTPS.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.entry_urls and args.random_count <= 0:
        raise SystemExit("Provide at least one --entry-url or a positive --random-count.")

    result = build_book(
        entry_urls=args.entry_urls,
        random_count=args.random_count,
        book_title=args.book_title,
        language=args.language,
        output_dir=Path(args.output_dir),
        insecure=args.insecure,
    )

    print(f"Book title: {result.book_title}")
    print(f"Entries: {result.entry_count}")
    print(f"Output directory: {result.output_dir}")
    print(f"EPUB: {result.epub_path}")


if __name__ == "__main__":
    main()
