"""JSON extraction utilities for LLM outputs.

This module provides a small, interview-friendly helper to extract a JSON
object or array from various LLM output formats (raw JSON, fenced code
blocks, or JSON embedded in free text).
"""

from typing import Any, Optional
import json
import re


def _try_parse(text: str) -> Optional[Any]:
    try:
        obj = json.loads(text)
        # only accept dict or list as valid JSON payloads
        if isinstance(obj, (dict, list)):
            return obj
    except Exception:
        return None
    return None


def _find_fenced_blocks(text: str):
    # Match triple backtick or tilde fences, capturing inner block
    pattern = re.compile(r"(?P<fence>```|~~~)\s*(?P<lang>\w+)?\n(?P<body>.*?)(?P=fence)", re.DOTALL)
    for m in pattern.finditer(text):
        yield m.group("body").strip()


def _extract_first_json_substring(text: str) -> Optional[str]:
    """Scan text and return the first substring that looks like a JSON object or array.

    This is a stack-based scanner that respects quoted strings and escapes so
    braces inside strings are ignored.
    """
    opening = {"{": "}", "[": "]"}
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch not in opening:
            i += 1
            continue
        # found potential start
        stack = [opening[ch]]
        j = i + 1
        in_string = False
        string_quote = None
        escape = False
        while j < n:
            c = text[j]
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif in_string:
                if c == string_quote:
                    in_string = False
                    string_quote = None
            else:
                if c == '"' or c == "'":
                    in_string = True
                    string_quote = c
                elif c in opening:
                    stack.append(opening[c])
                elif stack and c == stack[-1]:
                    stack.pop()
                    if not stack:
                        # substring from i to j (inclusive)
                        return text[i : j + 1]
            j += 1
        # no matching end found for this start, continue scanning
        i += 1
    return None


def extract_json(value: Any) -> dict[str, Any] | list[Any] | None:
    """Extract a JSON dict or list from various LLM output formats.

    - If `value` is already a dict or list, return it unchanged.
    - If `value` is not a string, return None.
    - If `value` is a raw JSON string, parse it.
    - If `value` contains markdown fenced code blocks, try each block.
    - Otherwise scan the text and extract the first JSON object/array substring,
      parse it, and return the parsed object.
    - Return None if parsing fails or no JSON found.
    """
    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # 1) Try parsing entire string as JSON
    parsed = _try_parse(text)
    if parsed is not None:
        return parsed

    # 2) Try fenced code blocks (```json ... ``` or ~~~)
    for block in _find_fenced_blocks(text):
        parsed = _try_parse(block)
        if parsed is not None:
            return parsed

    # 3) Extract first JSON substring from free text
    candidate = _extract_first_json_substring(text)
    if candidate:
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    return None
