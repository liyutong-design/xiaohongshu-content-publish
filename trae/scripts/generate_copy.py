#!/usr/bin/env python3
"""步骤1：小红书文案生成（对应 Coze 节点 190438）。

输入主题和作者名，输出笔记标题、发布正文、话题标签、内容领域。
结果写入 output/copy.json。LLM 不可用时退出码为 2。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import llm_client
from prompts.copy_prompt import COPY_SYSTEM_PROMPT, COPY_OUTPUT_INSTRUCTION, build_copy_user_prompt


def generate_copy(topic: str, author: str, options: dict = None) -> dict:
    system = COPY_SYSTEM_PROMPT + "\n\n" + COPY_OUTPUT_INSTRUCTION
    user = build_copy_user_prompt(topic, author, options)
    raw = llm_client.chat(system, user)
    note = llm_client.extract_json_object(raw)

    required = ("note_title", "note_body", "hashtags")
    for key in required:
        if not note.get(key):
            raise ValueError(f"copy generation missing field: {key}")
    if not isinstance(note["hashtags"], list):
        raise ValueError("hashtags must be a list")
    note["author"] = author
    note["topic"] = topic
    return note


def main() -> int:
    parser = argparse.ArgumentParser(description="生成小红书笔记文案（标题+正文+话题标签）")
    parser.add_argument("--topic", required=True, help="主题或原始内容")
    parser.add_argument("--author", required=True, help="作者名")
    parser.add_argument("--audience", default="", help="目标人群")
    parser.add_argument("--tone", default="", help="语气要求")
    parser.add_argument("--visual-style", default="", help="视觉风格")
    parser.add_argument("--key-points", default="", help="必须体现的重点")
    parser.add_argument("--avoid", default="", help="禁止出现的内容")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    options = {
        "audience": args.audience,
        "tone": args.tone,
        "visual_style": args.visual_style,
        "key_points": args.key_points,
        "avoid": args.avoid,
    }

    if not config.llm_available():
        print(f"ERROR: 环境变量 {config.LLM_API_KEY_ENV} 未配置，无法调用文案生成模型", file=sys.stderr)
        return 2

    try:
        note = generate_copy(args.topic, args.author, options)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "copy.json"
    out_file.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": str(out_file), "domain": note.get("domain"),
                      "note_title": note.get("note_title")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
