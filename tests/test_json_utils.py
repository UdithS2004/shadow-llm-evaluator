"""Unit tests for `extract_json` in `app.json_utils`.

These tests cover raw JSON, fenced blocks, embedded JSON in text,
nested structures, invalid inputs, and edge cases like braces inside
JSON strings.
"""

import pytest

from app.json_utils import extract_json


def test_raw_json_object():
    src = '{"a": 1, "b": "x"}'
    out = extract_json(src)
    assert isinstance(out, dict)
    assert out == {"a": 1, "b": "x"}


def test_raw_json_array():
    src = '[1, 2, 3]'
    out = extract_json(src)
    assert isinstance(out, list)
    assert out == [1, 2, 3]


def test_markdown_fenced_json():
    src = """Here is the output:
```json
{"result": [1,2,3], "ok": true}
```
More text.
"""
    out = extract_json(src)
    assert isinstance(out, dict)
    assert out == {"result": [1, 2, 3], "ok": True}


def test_text_containing_json_object():
    src = 'Note: the response was {"x": 10, "y": [1,2]} — end.'
    out = extract_json(src)
    assert isinstance(out, dict)
    assert out == {"x": 10, "y": [1, 2]}


def test_text_containing_json_array():
    src = 'Results: [ {"id":1}, {"id":2} ] appended.'
    out = extract_json(src)
    assert isinstance(out, list)
    assert out == [{"id": 1}, {"id": 2}]


def test_nested_json():
    src = '{"a": {"b": [{"c": 3}]}}'
    out = extract_json(src)
    assert isinstance(out, dict)
    assert out == {"a": {"b": [{"c": 3}]}}


def test_invalid_text_returns_none():
    assert extract_json('no json here') is None
    assert extract_json('not json {invalid: }') is None


def test_dict_input_returns_unchanged():
    obj = {"k": "v"}
    out = extract_json(obj)
    # Should return the same object (not a copy)
    assert out is obj


def test_list_input_returns_unchanged():
    obj = [1, 2, 3]
    out = extract_json(obj)
    assert out is obj


def test_braces_inside_json_strings():
    src = '{"text": "This string contains } and { braces and \\\"quotes\\\" inside"}'
    out = extract_json(src)
    assert isinstance(out, dict)
    assert out["text"].startswith("This string contains")
