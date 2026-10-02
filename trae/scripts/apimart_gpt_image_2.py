#!/usr/bin/env python3
"""Submit and poll an APIMart GPT-image-2 task without storing API keys."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "https://api.apimart.ai/v1"


def request_json(method: str, url: str, api_key: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        err_msg = (
            f"[HTTPError] status={exc.code}, reason={exc.reason}\n"
            f"[HTTPError] response body:\n{detail}"
        )
        try:
            print(err_msg, file=sys.stderr)
        except UnicodeEncodeError:
            sys.stderr.buffer.write(err_msg.encode("utf-8", errors="replace") + b"\n")
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def parse_task_id(response):
    data = response.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0].get("task_id")
    return None


def parse_image_urls(response):
    data = response.get("data", {})
    result = data.get("result", {}) if isinstance(data, dict) else {}
    images = result.get("images", []) if isinstance(result, dict) else []
    urls = []
    for image in images:
        value = image.get("url", []) if isinstance(image, dict) else []
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, list):
            urls.extend(item for item in value if isinstance(item, str))
    return urls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--size", default="3:4")
    parser.add_argument("--resolution", choices=("1k", "2k", "4k"), default="2k")
    parser.add_argument("--n", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--image-url", action="append", default=[])
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--max-wait", type=float, default=300.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = {
        "model": "gpt-image-2",
        "prompt": args.prompt,
        "n": args.n,
        "size": args.size,
        "resolution": args.resolution,
    }
    if args.image_url:
        payload["image_urls"] = args.image_url

    if args.dry_run:
        print(json.dumps({"url": f"{BASE_URL}/images/generations", "payload": payload}, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("APIMART_API_KEY")
    if not api_key:
        print("ERROR: APIMART_API_KEY is not configured in the local environment", file=sys.stderr)
        return 2

    try:
        submitted = request_json("POST", f"{BASE_URL}/images/generations", api_key, payload)
        task_id = parse_task_id(submitted)
        if not task_id:
            print(json.dumps(submitted, ensure_ascii=False, indent=2))
            print("ERROR: response did not include task_id", file=sys.stderr)
            return 1

        print(json.dumps({"status": "submitted", "task_id": task_id}, ensure_ascii=False))
        deadline = time.monotonic() + args.max_wait
        while time.monotonic() < deadline:
            task = request_json("GET", f"{BASE_URL}/tasks/{task_id}", api_key)
            data = task.get("data", {})
            status = data.get("status") if isinstance(data, dict) else None
            if status == "completed":
                print(json.dumps({"status": status, "task_id": task_id, "image_urls": parse_image_urls(task)}, ensure_ascii=False, indent=2))
                return 0
            if status == "failed":
                print(json.dumps(task, ensure_ascii=False, indent=2))
                return 1
            time.sleep(max(args.poll_interval, 0.5))
        print(json.dumps({"status": "timeout", "task_id": task_id}, ensure_ascii=False))
        return 3
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
