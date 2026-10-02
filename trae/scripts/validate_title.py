#!/usr/bin/env python3
"""Validate that two display lines preserve an original title exactly."""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--line1", required=True)
    parser.add_argument("--line2", required=True)
    args = parser.parse_args()
    if not args.line1 or not args.line2:
        print("FAIL: both title lines must be non-empty")
        return 1
    if args.line1 + args.line2 != args.original:
        print("FAIL: line1 + line2 does not exactly match original")
        return 1
    print("PASS: title characters are preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
