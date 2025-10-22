"""Minimal YAML parser supporting the subset used by environment profiles."""

from __future__ import annotations

from typing import Any, Tuple


class SimpleYAMLError(ValueError):
    """Raised when the YAML input cannot be parsed."""


def _strip_comments(line: str) -> str:
    result = []
    in_single = False
    in_double = False
    for char in line:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result)


def _prepare_lines(text: str) -> Tuple[str, ...]:
    processed = []
    for raw in text.splitlines():
        line = _strip_comments(raw).rstrip()
        if not line.strip():
            continue
        processed.append(line)
    return tuple(processed)


def _parse_scalar(token: str) -> Any:
    token = token.strip()
    if not token:
        return ""
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        return token[1:-1]
    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1]
    lowered = token.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if token.isdigit():
        return int(token)
    try:
        return float(token)
    except ValueError:
        return token


def _parse_block(lines: Tuple[str, ...], index: int, indent: int) -> Tuple[Any, int]:
    container: Any = None
    length = len(lines)
    while index < length:
        line = lines[index]
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent > indent:
            raise SimpleYAMLError(f"Unexpected indentation at line {index + 1}")
        stripped = line.strip()
        if stripped.startswith("- "):
            if container is None:
                container = []
            elif not isinstance(container, list):
                raise SimpleYAMLError("Cannot mix mappings and sequences")
            item_text = stripped[2:].strip()
            index += 1
            if item_text:
                container.append(_parse_scalar(item_text))
            else:
                item, index = _parse_block(lines, index, indent + 2)
                container.append(item)
        else:
            if container is None:
                container = {}
            elif not isinstance(container, dict):
                raise SimpleYAMLError("Cannot mix mappings and sequences")
            if ":" not in stripped:
                raise SimpleYAMLError(
                    f"Expected ':' in mapping entry at line {index + 1}"
                )
            key, value_text = stripped.split(":", 1)
            key = key.strip()
            value_text = value_text.strip()
            index += 1
            if value_text:
                container[key] = _parse_scalar(value_text)
            else:
                value, index = _parse_block(lines, index, indent + 2)
                container[key] = value
    if container is None:
        container = {}
    return container, index


def load(text: str) -> Any:
    """Parse *text* containing a limited YAML subset into Python primitives."""
    lines = _prepare_lines(text)
    data, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise SimpleYAMLError("Failed to consume entire document")
    return data


__all__ = ["SimpleYAMLError", "load"]
