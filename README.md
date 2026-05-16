# sep-to-ebook

THIS CODE WAS FULLY VIBECODED - ENJOY!

Minimal Python project that fetches Stanford Encyclopedia of Philosophy entries, extracts the article body plus bibliography, saves cleaned HTML/XHTML files, and packages them into an EPUB.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Example

```bash
python -m sep_to_ebook.cli \
  --entry-url https://plato.stanford.edu/entries/religion-epistemology/ \
  --book-title "SEP Sample" \
  --output-dir output
```

If your local network injects a self-signed TLS certificate, add `--insecure`.

## Random entries

```bash
python -m sep_to_ebook.cli \
  --random-count 10 \
  --book-title "SEP Random 1" \
  --output-dir output
```

The command writes:

- cleaned per-entry XHTML files
- a combined `book.xhtml`
- `book.epub`
