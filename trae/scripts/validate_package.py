#!/usr/bin/env python3
"""Validate deterministic structure of a Xiaohongshu four-image manifest."""

import json
import sys
from pathlib import Path

EXPECTED_ROLES = ["cover", "content-1", "content-2", "content-3"]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_package.py manifest.json")
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read manifest: {exc}")
        return 2

    errors: list[str] = []
    title = data.get("title", "")
    if not title or data.get("title_line1", "") + data.get("title_line2", "") != title:
        errors.append("title lines must be non-empty and preserve the title exactly")

    pages = data.get("pages", [])
    roles = [page.get("role") for page in pages if isinstance(page, dict)]
    if len(pages) != 4:
        errors.append("pages must contain exactly four entries")
    if roles != EXPECTED_ROLES:
        errors.append(f"page roles must be ordered as {EXPECTED_ROLES}")

    for page_index, page in enumerate(pages[1:4], start=1):
        sections = page.get("sections", []) if isinstance(page, dict) else []
        if len(sections) != 3:
            errors.append(f"content page {page_index} must contain exactly three sections")
            continue
        for section_index, section in enumerate(sections, start=1):
            body = section.get("body", "") if isinstance(section, dict) else ""
            length = len(body.strip())
            if not 90 <= length <= 160:
                errors.append(
                    f"content page {page_index} section {section_index} body length "
                    f"must be 90-160 characters; got {length}"
                )

    tags = data.get("hashtags", [])
    if not isinstance(tags, list) or not 5 <= len(tags) <= 10:
        errors.append("hashtags must be a list containing 5-10 entries")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: deterministic package checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
