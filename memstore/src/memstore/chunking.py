"""Split an entry's text into small chunks for search.

The default embedder reads only the first 256 tokens of its input, so a whole entry embeds as little more than its first
paragraph. Chunks are therefore kept to MAX_CHARS, and a table that has to be split repeats its header.
"""
import re

MAX_CHARS = 700


def split_body(body, max_chars=MAX_CHARS):
    """Pack paragraphs into parts of at most max_chars; an oversized paragraph is split by line, then by width."""
    parts, current = [], ""
    for para in re.split(r"\n\s*\n", body):
        for piece in _split_paragraph(para.strip(), max_chars):
            if current and len(current) + 2 + len(piece) > max_chars:
                parts.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
    if current:
        parts.append(current)
    return parts


def _split_paragraph(para, max_chars):
    if not para or len(para) <= max_chars:
        return [para] if para else []
    lines = para.splitlines()
    is_table = len(lines) > 2 and all(line.lstrip().startswith("|") for line in lines)
    header = "\n".join(lines[:2]) if is_table else ""
    rows = lines[2:] if is_table else lines
    pieces, current = [], header
    for line in rows:
        for part in ([line] if len(line) <= max_chars else [line[i:i + max_chars] for i in range(0, len(line), max_chars)]):
            candidate = f"{current}\n{part}" if current else part
            if current and len(candidate) > max_chars and current != header:
                pieces.append(current)
                current = f"{header}\n{part}" if header else part
            else:
                current = candidate
    if current and current != header:
        pieces.append(current)
    return pieces
