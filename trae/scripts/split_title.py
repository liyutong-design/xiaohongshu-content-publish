#!/usr/bin/env python3
"""步骤3：首页文字语义拆分（对应 Coze 节点 143075）。

把主标题、副标题各拆成两行，用 validate_title.py 做确定性校验；
校验失败时只重试拆分环节。结果写入 output/split.json。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import llm_client
from prompts.split_prompt import SPLIT_SYSTEM_PROMPT, build_split_user_prompt

SCRIPT_DIR = Path(__file__).resolve().parent


def _run_validator(original: str, line1: str, line2: str) -> bool:
    """调用 scripts/validate_title.py 做逐字符一致性校验。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_title.py"),
         "--original", original, "--line1", line1, "--line2", line2],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def split_title(title: str, subtitle: str = "", max_attempts: int = 3) -> dict:
    """LLM 语义拆分 + 确定性校验，失败只重试本环节。"""
    user = build_split_user_prompt(title, subtitle)
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        raw = llm_client.chat(SPLIT_SYSTEM_PROMPT, user)
        data = llm_client.extract_json_object(raw)
        t1 = (data.get("title1") or "").strip()
        t2 = (data.get("title2") or "").strip()
        s1 = (data.get("subtitle1") or "").strip()
        s2 = (data.get("subtitle2") or "").strip()

        if _run_validator(title, t1, t2):
            if not subtitle or _run_validator(subtitle, s1, s2) or (not s1 and not s2):
                return {"title1": t1, "title2": t2, "subtitle1": s1, "subtitle2": s2}
            last_error = "副标题拆分后与原文不一致"
        else:
            last_error = f"主标题拆分后与原文不一致：{t1}|{t2}"

        llm_client.warn(f"拆分校验失败（第{attempt}次）：{last_error}")
        user = build_split_user_prompt(title, subtitle) + \
            f"\n\n上次拆分未通过逐字符校验（{last_error}），请严格保留原字符重新拆分。"

    raise ValueError(f"标题拆分多次未通过校验：{last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="把主标题/副标题拆成封面用两行文字")
    parser.add_argument("--structure", default="", help="structure.json 路径")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    structure_path = Path(args.structure) if args.structure else out_dir / "structure.json"
    if not structure_path.exists():
        print(f"ERROR: 找不到 {structure_path}，请先运行 structure_content.py", file=sys.stderr)
        return 2
    structure = json.loads(structure_path.read_text(encoding="utf-8"))

    if not config.llm_available():
        print(f"ERROR: 环境变量 {config.LLM_API_KEY_ENV} 未配置", file=sys.stderr)
        return 2

    try:
        result = split_title(structure.get("title", ""), structure.get("subtitle", ""))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    result["title"] = structure.get("title", "")
    result["subtitle"] = structure.get("subtitle", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "split.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": str(out_file),
                      "title1": result["title1"], "title2": result["title2"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
