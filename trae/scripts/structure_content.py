#!/usr/bin/env python3
"""步骤2：内容结构化拆分（对应 Coze 节点 189374「元素成分」）。

读取 copy.json，输出 title/subtitle、3个页面标题、9组小标题+正文、
1个联想名词 + 2个关联名词。结果写入 output/structure.json。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import llm_client
from prompts.structure_prompt import STRUCTURE_SYSTEM_PROMPT, build_structure_user_prompt


def validate_structure(data: dict) -> list:
    """校验结构化结果的关键约束，返回错误列表（空列表表示通过）。"""
    errors = []
    title = (data.get("title") or "").strip()
    if not title:
        errors.append("缺少主标题 title")
    elif not config.COVER_TITLE_MIN <= len(title) <= config.COVER_TITLE_MAX:
        errors.append(f"主标题需 {config.COVER_TITLE_MIN}-{config.COVER_TITLE_MAX} 字，当前 {len(title)} 字")

    subtitle = (data.get("subtitle") or "").strip()
    if not subtitle:
        errors.append("缺少副标题 subtitle")
    elif not config.SUBTITLE_MIN <= len(subtitle) <= config.SUBTITLE_MAX:
        errors.append(f"副标题需 {config.SUBTITLE_MIN}-{config.SUBTITLE_MAX} 字，当前 {len(subtitle)} 字")

    for i in range(1, config.SECTION_COUNT + 1):
        sub = (data.get(f"sub_title{i}") or "").strip()
        body = (data.get(f"content{i}") or "").strip()
        if not sub:
            errors.append(f"缺少小标题 sub_title{i}")
        if not body:
            errors.append(f"缺少正文 content{i}")
        elif not config.SECTION_BODY_MIN <= len(body) <= config.SECTION_BODY_MAX:
            errors.append(f"content{i} 需 {config.SECTION_BODY_MIN}-{config.SECTION_BODY_MAX} 字，当前 {len(body)} 字")

    for key in ("main_image", "element_img1", "element_img2"):
        if not (data.get(key) or "").strip():
            errors.append(f"缺少视觉元素 {key}")
    for key in ("page_title1", "page_title2", "page_title3"):
        if not (data.get(key) or "").strip():
            errors.append(f"缺少页面标题 {key}")
    return errors


def structure_content(note: dict, author: str, max_attempts: int = 3) -> dict:
    """调用 LLM 做结构化拆分，字数不合格时局部重试该步骤。"""
    user = build_structure_user_prompt(note, author)
    last_errors = []
    for attempt in range(1, max_attempts + 1):
        raw = llm_client.chat(STRUCTURE_SYSTEM_PROMPT, user)
        data = llm_client.extract_json_object(raw)
        errors = validate_structure(data)
        if not errors:
            return data
        last_errors = errors
        llm_client.warn(f"结构化校验未通过（第{attempt}次）：{'；'.join(errors)}")
        # 把错误反馈给模型，只重试本环节
        user = build_structure_user_prompt(note, author) + \
            "\n\n上次输出存在以下问题，请修正后重新输出完整 JSON：\n" + "\n".join(last_errors)
    raise ValueError("结构化拆分多次未通过校验：" + "；".join(last_errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="把笔记文案拆分为四图结构化内容")
    parser.add_argument("--copy", default="", help="copy.json 路径，默认 <output-dir>/copy.json")
    parser.add_argument("--author", default="", help="作者名（默认取 copy.json 中的 author）")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    copy_path = Path(args.copy) if args.copy else out_dir / "copy.json"
    if not copy_path.exists():
        print(f"ERROR: 找不到文案文件 {copy_path}，请先运行 generate_copy.py", file=sys.stderr)
        return 2
    note = json.loads(copy_path.read_text(encoding="utf-8"))
    author = args.author or note.get("author", "")

    if not config.llm_available():
        print(f"ERROR: 环境变量 {config.LLM_API_KEY_ENV} 未配置", file=sys.stderr)
        return 2

    try:
        data = structure_content(note, author)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    data["author"] = author
    data["note_title"] = note.get("note_title", "")
    data["note_body"] = note.get("note_body", "")
    data["hashtags"] = note.get("hashtags", [])

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "structure.json"
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": str(out_file), "title": data["title"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
