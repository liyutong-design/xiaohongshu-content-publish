#!/usr/bin/env python3
"""步骤6：整理四图并生成 manifest.json 与 publish-copy.txt，然后运行质检。

manifest.json 结构兼容 scripts/validate_package.py 的全部检查项。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def build_manifest(out_dir: Path) -> dict:
    structure = json.loads((out_dir / "structure.json").read_text(encoding="utf-8"))
    split = json.loads((out_dir / "split.json").read_text(encoding="utf-8"))
    visuals_path = out_dir / "visuals.json"
    visuals = json.loads(visuals_path.read_text(encoding="utf-8")) if visuals_path.exists() \
        else {"elements": {}}

    image_files = {
        "cover": "01-cover.png",
        "content-1": "02-content-1.png",
        "content-2": "03-content-2.png",
        "content-3": "04-content-3.png",
    }

    pages = [{
        "role": "cover",
        "file": image_files["cover"],
        "file_exists": (out_dir / image_files["cover"]).exists(),
        "elements": {k: v.get("status") for k, v in visuals.get("elements", {}).items()},
    }]
    for i in range(1, 4):
        sections = []
        for n in range(i * 3 - 2, i * 3 + 1):
            sections.append({
                "subtitle": structure.get(f"sub_title{n}", ""),
                "body": structure.get(f"content{n}", ""),
            })
        pages.append({
            "role": f"content-{i}",
            "file": image_files[f"content-{i}"],
            "file_exists": (out_dir / image_files[f"content-{i}"]).exists(),
            "page_title": structure.get(f"page_title{i}", ""),
            "sections": sections,
        })

    return {
        "topic": structure.get("note_title", ""),
        "author": structure.get("author", ""),
        "domain": structure.get("domain", ""),
        "title": structure.get("title", ""),
        "title_line1": split.get("title1", ""),
        "title_line2": split.get("title2", ""),
        "subtitle": structure.get("subtitle", ""),
        "subtitle_line1": split.get("subtitle1", ""),
        "subtitle_line2": split.get("subtitle2", ""),
        "note_body": structure.get("note_body", ""),
        "hashtags": structure.get("hashtags", []),
        "pages": pages,
    }


def write_publish_copy(manifest: dict, out_dir: Path) -> Path:
    tags = " ".join("#" + t for t in manifest.get("hashtags", []))
    text = (
        f"标题：{manifest.get('title', '')}\n\n"
        f"正文：\n{manifest.get('note_body', '')}\n\n"
        f"话题标签：\n{tags}\n"
    )
    path = out_dir / "publish-copy.txt"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 manifest.json / publish-copy.txt 并运行质检")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.output_dir)

    for name in ("structure.json", "split.json"):
        if not (out_dir / name).exists():
            print(f"ERROR: 找不到 {out_dir / name}，请先完成前序步骤", file=sys.stderr)
            return 2

    manifest = build_manifest(out_dir)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    copy_path = write_publish_copy(manifest, out_dir)

    # 运行确定性质检
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "validate_package.py"),
         str(manifest_path)],
        capture_output=True, text=True,
    )
    check = {"returncode": result.returncode,
             "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}

    print(json.dumps({
        "status": "ok" if result.returncode == 0 else "check_failed",
        "manifest": str(manifest_path),
        "publish_copy": str(copy_path),
        "check": check,
    }, ensure_ascii=False, indent=2))
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
