"""Document loading and text cleaning."""

import re

from .models import Document
from .paths import BEDTIMENEWS_ARCHIVE_CONTENTS_DIR


def load_document(doc_id: str) -> Document:
    """Load a single markdown document by its doc_id.

    Args:
        doc_id: Document ID (e.g., "960" or "main/901-1000/960")

    Returns:
        Document object
    """
    # Construct file path from doc_id
    file_path = BEDTIMENEWS_ARCHIVE_CONTENTS_DIR / f"{doc_id}.md"

    # Read file content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Clean text (includes removing YAML front matter)
    text = clean_text(content)

    # Generate unique ID
    doc_unique_id = f"doc_{doc_id.replace('/', '_')}"

    return Document(
        id=doc_unique_id,
        file_path=str(file_path),
        doc_id=doc_id,
        text=text,
    )


def clean_text(text: str) -> str:
    """Clean text content: remove YAML front matter, HTML, normalize whitespace.

    Args:
        text: Raw text content

    Returns:
        Cleaned text
    """
    # Remove YAML front matter (--- ... ---)
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        text = text[match.end() :]

    # Remove HTML sections
    text = _remove_html_sections(text)

    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove multiple consecutive blank lines
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def _remove_html_sections(text: str) -> str:
    """Remove HTML sections and embedded content.

    Args:
        text: Markdown text with potential HTML

    Returns:
        Text with HTML sections removed
    """
    # Remove the Tabs section with video embeds
    text = re.sub(
        r"#\s+Tabs\s+\{\.tabset\}.*?(?=\n#{1,6}\s+|\Z)", "", text, flags=re.DOTALL
    )

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove standalone HTML tags (div, iframe, etc.)
    text = re.sub(
        r"<(?:div|iframe|span)[^>]*>.*?</(?:div|iframe|span)>",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"<(?:div|iframe|span)[^>]*/?>", "", text)

    # Remove any remaining empty div tags
    text = re.sub(r"<div[^>]*>\s*</div>", "", text, flags=re.DOTALL)

    # Remove font tags but keep inner text
    text = re.sub(r"<font[^>]*>(.*?)</font>", r"\1", text, flags=re.DOTALL)

    # Remove any remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove Markdown image syntax: ![alt text](url)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

    # Remove standalone image placeholders
    text = re.sub(r"^图片\s*$", "", text, flags=re.MULTILINE)

    return text
