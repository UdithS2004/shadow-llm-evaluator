"""Evaluation helpers for comparing LLM responses.

This module contains compact helpers used by the background worker. The
functions operate on already-copied data (no FastAPI `Request` objects) and
are intentionally small for interview settings.
"""

import json
import logging
from typing import Any, Optional

from app.json_utils import extract_json


def normalize_json(value: Any) -> Optional[str]:
    """Extract JSON from `value` and return a canonical JSON string.

    Uses `extract_json` to parse the input. If extraction fails, returns
    `None`. Otherwise returns `json.dumps(obj, sort_keys=True, separators=(",",":"))`.
    """
    obj = extract_json(value)
    if obj is None:
        return None
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except Exception:
        return None


def responses_match(primary: Any, candidate: Any) -> bool:
    """Return True if the normalized primary and candidate responses match.

    If either response cannot be normalized (extraction/parsing failure),
    the function returns False.
    """
    n1 = normalize_json(primary)
    n2 = normalize_json(candidate)
    if n1 is None or n2 is None:
        return False
    return n1 == n2


def log_mismatch(request_id: str, primary: Any, candidate: Any) -> None:
    """Log a warning for mismatched LLM outputs.

    The log entry includes `request_id` and the extracted primary/candidate
    JSON values in the `extra` dict for structured logging.
    """
    logger = logging.getLogger(__name__)
    p_obj = extract_json(primary)
    c_obj = extract_json(candidate)
    logger.warning(
        "LLM mismatch",
        extra={"request_id": request_id, "primary_json": p_obj, "candidate_json": c_obj},
    )
