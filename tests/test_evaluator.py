"""Unit tests for `app.evaluator` helpers."""

import pytest

from app.evaluator import normalize_json, responses_match


def test_same_json_different_key_order_matches():
    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert normalize_json(a) == normalize_json(b)
    assert responses_match(a, b)


def test_different_json_values_do_not_match():
    a = {"a": 1}
    b = {"a": 2}
    assert not responses_match(a, b)


def test_markdown_fenced_json_matches_raw_json():
    fenced = """Some text
```json
{"x": 10, "y": [1,2]}
```
End."""
    raw = {"x": 10, "y": [1, 2]}
    assert responses_match(fenced, raw)


def test_text_containing_json_matches_raw_json():
    text = 'Note: result was {"ok": true, "v": 3} for the request.'
    raw = {"ok": True, "v": 3}
    assert responses_match(text, raw)


def test_invalid_json_compared_with_valid_does_not_match():
    invalid = 'no json here'
    valid = {"k": "v"}
    assert not responses_match(invalid, valid)


def test_both_invalid_jsons_do_not_match():
    a = 'not json {broken: }'
    b = 'still nothing'
    assert not responses_match(a, b)


def test_normalize_json_canonical_string():
    a = {"z": 0, "a": [2, 1]}
    b = {"a": [2, 1], "z": 0}
    na = normalize_json(a)
    nb = normalize_json(b)
    assert isinstance(na, str) and isinstance(nb, str)
    assert na == nb
