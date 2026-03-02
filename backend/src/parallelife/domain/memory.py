from __future__ import annotations

import re


_REQUEST_PATTERNS = [
    r"\?",
    r"吗",
    r"能不能",
    r"可以吗",
    r"帮我",
    r"请你",
    r"请帮",
    r"麻烦",
    r"希望你",
]

_EMOTION_PATTERNS = [
    r"喜欢",
    r"爱",
    r"讨厌",
    r"难过",
    r"伤心",
    r"焦虑",
    r"开心",
    r"生气",
    r"害怕",
    r"谢谢",
    r"抱歉",
]


def estimate_importance(content: str) -> int:
    """
    MVP heuristic importance score (1-10).
    PRD intent:
    - keep recent 10 messages
    - keep "important" longer
    - expire normal messages after 24h
    """
    text = (content or "").strip()
    if not text:
        return 1

    score = 4
    if len(text) >= 80:
        score += 2
    if len(text) >= 200:
        score += 1

    if any(re.search(p, text) for p in _REQUEST_PATTERNS):
        score += 2

    if any(re.search(p, text) for p in _EMOTION_PATTERNS):
        score += 2

    if any(ch.isdigit() for ch in text):
        score += 1

    return max(1, min(10, score))

