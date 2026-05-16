# sep-to-ebook

Short documentation for the first working version.

## What it does

`sep-to-ebook` fetches Stanford Encyclopedia of Philosophy entries, extracts:

- title
- publication line
- main article body
- bibliography

Then it writes:

- per-entry XHTML files
- one combined `book.xhtml`
- one `book.epub`

## Setup

```bash
cd /Users/wiktormorawski/Work/sep-to-ebook
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Usage

Single entry:

```bash
python -m sep_to_ebook.cli \
  --entry-url https://plato.stanford.edu/entries/religion-epistemology/ \
  --book-title "SEP Sample" \
  --output-dir output
```

Random entries:

```bash
python -m sep_to_ebook.cli \
  --random-count 3 \
  --book-title "SEP Random 3" \
  --output-dir output
```

## Output structure

Example output directory:

```text
output/sep-sample/
  book.epub
  book.xhtml
  html/
    01-some-entry.xhtml
    02-another-entry.xhtml
```

## Notes

- `--random-count` uses SEP's live `Random Entry` endpoint.
- The first iteration is intentionally simple: it strips SEP navigation blocks and keeps the article plus bibliography.
- If Python hits a certificate-verification error, the fetch now retries automatically without verification and prints a warning.
- You can still force this behavior explicitly with `--insecure`.

## Validation

Basic test:

```bash
python -m unittest discover -s tests
```
