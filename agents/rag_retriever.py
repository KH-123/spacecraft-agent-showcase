"""
Local Markdown knowledge retriever for the RAG-enhanced design advisor.

Reads ``.md`` files from ``docs/rag_knowledge/`` and returns relevant text
snippets based on simple keyword matching.  This is a minimal local retrieval
layer — no vector database, no embedding model, no external API.

Graceful fallback: if no knowledge directory exists, no files are found, or
no snippet matches the query, an empty list is returned.
"""

from __future__ import annotations

import glob
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_DIR = os.path.join("docs", "rag_knowledge")


def _list_knowledge_files(knowledge_dir: str) -> List[str]:
    """Return all ``.md`` file paths under *knowledge_dir* (non-recursive)."""
    pattern = os.path.join(knowledge_dir, "*.md")
    return sorted(glob.glob(pattern))


def _read_file(path: str) -> Optional[str]:
    """Read a text file; return ``None`` on any error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Cannot read knowledge file %s: %s", path, exc)
        return None


def _split_into_snippets(text: str, min_chars: int = 80) -> List[Dict[str, Any]]:
    """Split Markdown into heading-delimited snippets with line numbers."""
    lines = text.splitlines()
    snippets: List[Dict[str, Any]] = []
    current_start = 1
    current_lines: List[str] = []

    def flush(end_line: int) -> None:
        if not current_lines:
            return
        snippet_text = "\n".join(current_lines).strip()
        if len(snippet_text) < min_chars:
            return
        heading_match = re.search(r"^#{1,3}\s+(.+)", snippet_text, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else ""
        snippets.append(
            {
                "text": snippet_text,
                "heading": heading,
                "start_line": current_start,
                "end_line": end_line,
            }
        )

    heading_pattern = re.compile(r"^#{2,3}\s+")
    for line_no, line in enumerate(lines, start=1):
        if heading_pattern.match(line) and current_lines:
            flush(line_no - 1)
            current_start = line_no
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        flush(len(lines))

    if snippets:
        return snippets

    stripped = text.strip()
    if len(stripped) < min_chars:
        return []
    return [
        {
            "text": stripped,
            "heading": "",
            "start_line": 1,
            "end_line": max(len(lines), 1),
        }
    ]


def _keyword_score(snippet: str, keywords: List[str]) -> int:
    """Return a simple count of how many *keywords* appear in *snippet*."""
    lower = snippet.lower()
    return sum(1 for kw in keywords if kw.lower() in lower)


def retrieve(
    query: str,
    *,
    knowledge_dir: str = DEFAULT_KNOWLEDGE_DIR,
    max_snippets: int = 3,
    min_score: int = 1,
) -> List[Dict[str, Any]]:
    """Retrieve relevant Markdown snippets for *query*.

    Parameters
    ----------
    query : str
        Free-text query (e.g. "power subsystem typical values").
    knowledge_dir : str
        Path to the directory containing ``.md`` knowledge files.
    max_snippets : int
        Maximum number of snippets to return.
    min_score : int
        Minimum keyword-match score for a snippet to be included.

    Returns
    -------
    List[Dict[str, Any]]
        Each entry::

            {
                "source_file": "docs/rag_knowledge/power.md",
                "heading": "Solar Array Sizing",
                "start_line": 12,
                "end_line": 28,
                "snippet": "...text...",
                "short_snippet": "...short text...",
                "score": 3
            }

        Empty list when no relevant snippet is found.
    """
    files = _list_knowledge_files(knowledge_dir)
    if not files:
        logger.info("No knowledge files found under %s", knowledge_dir)
        return []

    keywords = [w.strip() for w in re.split(r"[\s,;]+", query) if len(w.strip()) > 1]

    candidates: List[Dict[str, Any]] = []

    for filepath in files:
        content = _read_file(filepath)
        if content is None:
            continue

        snippets = _split_into_snippets(content)
        for snippet_data in snippets:
            snippet = snippet_data["text"]
            score = _keyword_score(snippet, keywords)
            if score < min_score:
                continue

            # Extract the first heading line from the snippet for context
            heading = snippet_data.get("heading") or os.path.basename(filepath)
            start_line = int(snippet_data.get("start_line") or 1)
            end_line = int(snippet_data.get("end_line") or start_line)
            short_snippet = " ".join(snippet.split())[:220]

            candidates.append(
                {
                    "source_file": os.path.relpath(filepath),
                    "heading": heading,
                    "start_line": start_line,
                    "end_line": end_line,
                    "snippet": snippet[:500],  # keep snippets short
                    "short_snippet": short_snippet,
                    "score": score,
                }
            )

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:max_snippets]


def retrieve_combined(
    query: str,
    *,
    knowledge_dir: str = DEFAULT_KNOWLEDGE_DIR,
    max_snippets: int = 3,
    min_score: int = 1,
) -> str:
    """Convenience wrapper: return retrieved snippets joined as a single string.

    Returns an empty string when nothing is found.
    """
    results = retrieve(
        query,
        knowledge_dir=knowledge_dir,
        max_snippets=max_snippets,
        min_score=min_score,
    )
    if not results:
        return ""

    parts: List[str] = []
    for r in results:
        start_line = r.get("start_line")
        end_line = r.get("end_line")
        if start_line and end_line and end_line != start_line:
            line_ref = f"L{start_line}-L{end_line}"
        elif start_line:
            line_ref = f"L{start_line}"
        else:
            line_ref = ""
        source_ref = f"{r['source_file']}:{line_ref}" if line_ref else r["source_file"]
        parts.append(f"--- {source_ref} - {r['heading']}")
        parts.append(r["snippet"])
    return "\n\n".join(parts)
