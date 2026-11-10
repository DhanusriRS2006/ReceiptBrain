"""
Robust JSON extraction from LLM output.

LLMs often return JSON wrapped in markdown, preceded by chatter, or cut off
when the token limit is hit. extract_json() survives all three.
"""
import json
import re


def _find_object_end(text: str, start: int):
    """Index just after the '}' matching the '{' at `start`, or None if unterminated.
    Braces inside strings are ignored."""
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def repair_truncated(s: str) -> str:
    """Best-effort fix for JSON cut off mid-way: close strings, drop dangling
    keys/commas, then close every open { and [ in the right order."""
    stack, in_str, esc = [], False, False
    for c in s:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "{[":
            stack.append("}" if c == "{" else "]")
        elif c in "}]" and stack:
            stack.pop()
    if in_str:
        s += '"'
    s = s.rstrip()
    s = re.sub(r"[,:]\s*$", "", s)
    s = re.sub(r',\s*"[^"]*"\s*$', "", s)  # dangling key with no value
    return s + "".join(reversed(stack))


def extract_json(text: str) -> dict:
    """Return the first JSON object found in `text`. Raises ValueError if none."""
    if not text:
        raise ValueError("empty model response")
    text = re.sub(r"```(?:json)?", "", text).strip()
    for m in re.finditer(r"\{", text):
        start = m.start()
        end = _find_object_end(text, start)
        candidate = text[start:end] if end else text[start:]
        for attempt in (candidate, repair_truncated(candidate)):
            try:
                obj = json.loads(attempt)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
    raise ValueError(f"no JSON object found in: {text[:120]!r}")
