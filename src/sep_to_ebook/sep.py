from __future__ import annotations

import ssl
from dataclasses import dataclass
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, NavigableString, Tag
from latex2mathml.converter import convert as latex_to_mathml

SEP_ROOT = "https://plato.stanford.edu"
RANDOM_ENTRY_URL = f"{SEP_ROOT}/cgi-bin/encyclopedia/random"
USER_AGENT = "sep-to-ebook/0.1 (+https://plato.stanford.edu/)"
SKIP_SECTION_TITLES = {
    "academic tools",
    "other internet resources",
    "related entries",
    "author and citation info",
}
BLOCK_MATH_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
INLINE_MATH_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
TAG_RE = re.compile(r"\\tag\{([^{}]+)\}")
REF_RE = re.compile(r"\\ref\{([^{}]+)\}")


@dataclass(slots=True)
class SepEntry:
    source_url: str
    slug: str
    title: str
    publication_info: str
    summary_html: str
    body_html: str
    bibliography_html: str

    def to_xhtml_fragment(self) -> str:
        parts = ["<section>"]
        parts.append(f"<h2>{escape_xml(self.title)}</h2>")
        if self.publication_info:
            parts.append(f"<p><em>{escape_xml(self.publication_info)}</em></p>")
        if self.summary_html:
            parts.append(self.summary_html)
        parts.append(self.body_html)
        if self.bibliography_html:
            parts.append("<h3>Bibliography</h3>")
            parts.append(self.bibliography_html)
        parts.append(f"<p><a href='{escape_xml(self.source_url)}'>{escape_xml(self.source_url)}</a></p>")
        parts.append("</section>")
        return "\n".join(parts)

    def to_xhtml_document(self) -> str:
        return "\n".join(
            [
                "<html xmlns='http://www.w3.org/1999/xhtml'>",
                "<head>",
                f"<title>{escape_xml(self.title)}</title>",
                "<meta charset='utf-8'/>",
                "</head>",
                "<body>",
                self.to_xhtml_fragment(),
                "</body>",
                "</html>",
            ]
        )


def fetch_entries(entry_urls: list[str], random_count: int, insecure: bool = False) -> list[SepEntry]:
    urls = normalize_entry_urls(entry_urls)
    target_count = len(urls) + random_count
    seen = set(urls)

    while len(urls) < target_count:
        random_url = resolve_random_entry_url(insecure=insecure)
        if random_url not in seen:
            urls.append(random_url)
            seen.add(random_url)

    return [extract_entry(fetch_html(url, insecure=insecure), source_url=url) for url in urls]


def normalize_entry_urls(entry_urls: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for url in entry_urls:
        clean = url.strip()
        if clean:
            normalized.append(clean.rstrip("/") + "/")
    return normalized


def resolve_random_entry_url(insecure: bool = False) -> str:
    response = fetch_response(RANDOM_ENTRY_URL, insecure=insecure)
    return response.geturl().rstrip("/") + "/"


def fetch_html(url: str, insecure: bool = False) -> str:
    with fetch_response(url, insecure=insecure) as response:
        return response.read().decode("utf-8")


def fetch_response(url: str, insecure: bool = False):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl._create_unverified_context() if insecure else None
    return urlopen(request, context=context)


def extract_entry(html: str, source_url: str) -> SepEntry:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.find("h1")
    if title_node is None:
        raise ValueError(f"No title found for {source_url}")

    article_nodes = collect_article_nodes(title_node)
    label_map = collect_math_labels(article_nodes)
    publication_info = extract_publication_info(article_nodes)
    summary_nodes, body_nodes, bibliography_nodes = split_article_nodes(article_nodes)

    return SepEntry(
        source_url=source_url,
        slug=slug_from_url(source_url),
        title=title_node.get_text(" ", strip=True),
        publication_info=publication_info,
        summary_html=render_nodes(summary_nodes, source_url, label_map),
        body_html=render_nodes(body_nodes, source_url, label_map),
        bibliography_html=render_nodes(bibliography_nodes, source_url, label_map),
    )


def collect_article_nodes(title_node: Tag) -> list[Tag]:
    nodes: list[Tag] = []
    for sibling in title_node.next_siblings:
        if isinstance(sibling, NavigableString):
            text = sibling.strip()
            if text:
                wrapper = BeautifulSoup("", "html.parser").new_tag("p")
                wrapper.string = text
                nodes.append(wrapper)
            continue

        if not isinstance(sibling, Tag):
            continue

        text = sibling.get_text(" ", strip=True)
        if "copyright" in text.lower() and "stanford" in text.lower():
            break

        nodes.append(sibling)

    return nodes


def extract_publication_info(article_nodes: list[Tag]) -> str:
    for node in article_nodes[:3]:
        text = node.get_text(" ", strip=True)
        if text.lower().startswith("first published"):
            return text
    return ""


def split_article_nodes(article_nodes: list[Tag]) -> tuple[list[Tag], list[Tag], list[Tag]]:
    summary_nodes: list[Tag] = []
    body_nodes: list[Tag] = []
    bibliography_nodes: list[Tag] = []

    first_h2_seen = False
    in_bibliography = False
    in_skipped_tail = False

    for node in article_nodes:
        if is_publication_node(node):
            continue

        if is_table_of_contents_node(node) and not first_h2_seen:
            continue

        if is_separator_node(node):
            continue

        if node.name == "h2":
            first_h2_seen = True
            heading = normalize_heading(node.get_text(" ", strip=True))
            if heading == "bibliography":
                in_bibliography = True
                continue
            if heading in SKIP_SECTION_TITLES:
                in_skipped_tail = True
                continue
            in_bibliography = False

        if in_skipped_tail:
            continue

        if not first_h2_seen:
            if should_keep_summary_node(node):
                summary_nodes.append(node)
            continue

        if in_bibliography:
            bibliography_nodes.append(node)
        else:
            body_nodes.append(node)

    return summary_nodes, body_nodes, bibliography_nodes


def is_publication_node(node: Tag) -> bool:
    return node.get_text(" ", strip=True).lower().startswith("first published")


def is_table_of_contents_node(node: Tag) -> bool:
    lists = [node] if node.name in {"ul", "ol"} else node.find_all(["ul", "ol"])
    if not lists:
        return False

    hrefs = [anchor.get("href", "") for anchor in node.find_all("a")]
    if not hrefs or not all(href.startswith("#") for href in hrefs):
        return False

    text = node.get_text(" ", strip=True).lower()
    return "entry contents" in text or node.find("hr") is not None or len(hrefs) >= 5


def is_separator_node(node: Tag) -> bool:
    text = node.get_text(" ", strip=True)
    return node.name == "hr" or text == "* * *"


def should_keep_summary_node(node: Tag) -> bool:
    return node.name in {"p", "div", "blockquote"}


def normalize_heading(text: str) -> str:
    return " ".join(text.lower().split())


def render_nodes(nodes: list[Tag], source_url: str, label_map: dict[str, str]) -> str:
    rendered: list[str] = []
    for node in nodes:
        fragment = BeautifulSoup(str(node), "html.parser")
        sanitize_fragment(fragment, source_url, label_map)
        html = "".join(str(child) for child in fragment.contents).strip()
        if html:
            rendered.append(html)
    return "\n".join(rendered)


def sanitize_fragment(fragment: BeautifulSoup, source_url: str, label_map: dict[str, str]) -> None:
    for tag in fragment.find_all(["script", "style", "noscript", "form", "button", "img", "svg"]):
        tag.decompose()

    for tag in fragment.find_all(True):
        for attr in list(tag.attrs):
            if attr in {"class", "id", "style", "role", "aria-label", "onclick"}:
                del tag.attrs[attr]

        if tag.name == "a":
            href = tag.get("href")
            if not href:
                tag.unwrap()
                continue
            if href.startswith("#"):
                tag.unwrap()
                continue
            tag["href"] = urljoin(source_url, href)

    for empty in fragment.find_all(["p", "div", "span", "li"]):
        if not empty.get_text(" ", strip=True) and not empty.find("a"):
            empty.decompose()

    transform_math_nodes(fragment, label_map)


def collect_math_labels(nodes: list[Tag]) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for node in nodes:
        text = node.get_text("\n", strip=False)
        for match in BLOCK_MATH_RE.finditer(text):
            formula = match.group(1)
            label_match = LABEL_RE.search(formula)
            tag_match = TAG_RE.search(formula)
            if label_match and tag_match:
                label_map[label_match.group(1)] = tag_match.group(1)
    return label_map


def transform_math_nodes(fragment: BeautifulSoup, label_map: dict[str, str]) -> None:
    for text_node in list(fragment.find_all(string=True)):
        if not isinstance(text_node, NavigableString):
            continue
        text = str(text_node)
        if "\\(" not in text and "\\[" not in text:
            continue

        replacements = parse_text_with_math(fragment, text, label_map)
        if replacements is None:
            continue

        for replacement in replacements:
            text_node.insert_before(replacement)
        text_node.extract()


def parse_text_with_math(fragment: BeautifulSoup, text: str, label_map: dict[str, str]):
    pieces: list[object] = []
    position = 0
    while position < len(text):
        next_inline = INLINE_MATH_RE.search(text, position)
        next_block = BLOCK_MATH_RE.search(text, position)
        matches = [match for match in [next_inline, next_block] if match is not None]
        if not matches:
            if position < len(text):
                pieces.append(NavigableString(text[position:]))
            break

        match = min(matches, key=lambda item: item.start())
        if match.start() > position:
            pieces.append(NavigableString(text[position:match.start()]))

        display = "block" if match.re is BLOCK_MATH_RE else "inline"
        pieces.append(build_math_replacement(fragment, match.group(1), label_map, display))
        position = match.end()

    return pieces


def build_math_replacement(
    fragment: BeautifulSoup,
    formula: str,
    label_map: dict[str, str],
    display: str,
):
    prepared, equation_number = prepare_formula(formula, label_map)
    mathml = latex_to_mathml(prepared, display=display)
    math_fragment = BeautifulSoup(mathml, "html.parser")
    math_tag = math_fragment.find("math")
    if math_tag is None:
        return NavigableString(formula)

    if display == "inline":
        return math_tag

    wrapper = fragment.new_tag("div", attrs={"class": "math-display"})
    wrapper.append(math_tag)
    if equation_number:
        number = fragment.new_tag("span", attrs={"class": "eq-number"})
        number.string = f"({equation_number})"
        wrapper.append(number)
    return wrapper


def prepare_formula(formula: str, label_map: dict[str, str]) -> tuple[str, str | None]:
    equation_number = None
    tag_match = TAG_RE.search(formula)
    if tag_match:
        equation_number = tag_match.group(1)

    resolved = REF_RE.sub(lambda match: label_map.get(match.group(1), match.group(1)), formula)
    resolved = LABEL_RE.sub("", resolved)
    resolved = TAG_RE.sub("", resolved)
    resolved = resolved.replace(r"\mathbin{|}", r" \mid ")
    resolved = resolved.strip()
    return resolved, equation_number


def slug_from_url(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[-1] if parts else "entry"


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
