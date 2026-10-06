"""Offline retrieval from explicitly approved, source-identified knowledge JSONL."""
from __future__ import annotations
import json
from pathlib import Path
import re

WORDS = re.compile(r"[a-z0-9]{3,}")

def retrieve(query: str, path: Path, *, limit: int = 3) -> tuple[dict, ...]:
    if not isinstance(query, str) or not 1 <= limit <= 3:
        raise ValueError("Invalid retrieval request")
    if not path.exists():
        return ()
    terms = set(WORDS.findall(query.casefold()))
    hits = []
    seen = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("approved") is not True:
                continue
            sid, excerpt = item.get("source_id"), item.get("excerpt")
            if not isinstance(sid, str) or not sid or sid in seen or not isinstance(excerpt, str) or not excerpt.strip() or len(excerpt) > 600:
                raise ValueError("Invalid approved knowledge record")
            if not isinstance(item.get("title"), str) or not isinstance(item.get("version"), str):
                raise ValueError("Approved knowledge needs title and version")
            seen.add(sid)
            overlap = len(terms & set(WORDS.findall((item["title"] + " " + excerpt).casefold())))
            if overlap:
                hits.append((overlap, sid, {"approved": True, "source_id": sid,
                                            "excerpt": excerpt, "title": item["title"],
                                            "version": item["version"]}))
    hits.sort(key=lambda x: (-x[0], x[1]))
    return tuple(hit[2] for hit in hits[:limit])
