#!/usr/bin/env python3
"""小红书一键生成图文并发布 - 主入口。

按顺序执行完整流程：
  1. 生成小红书文案（标题+正文+话题标签）
  2. 内容结构化拆分（9组小标题+正文、视觉元素）
  3. 首页文字语义拆分（标题两行、副标题两行）
  4. 生成视觉元素素材（主视觉 + 2个辅助元素）
  5. 排版四图（1封面 + 3内容页）
  6. 整理输出并质检
  7. 等待用户确认后发布（或手动交付）

用法：
  python main.py --topic "大学生熬夜自救" --author 李悦彤
  python main.py --topic "..." --author ... --audience 大学生 --tone 亲切
  python main.py --resume-from structure --output-dir output

所有 API 密钥仅通过环境变量读取：DOUBAO_API_KEY、APIMART_API_KEY。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import config

STEP_ORDER = [
    ("copy", "步骤1/7 生成小红书文案"),
    ("structure", "步骤2/7 内容结构化拆分"),
    ("split", "步骤3/7 首页文字语义拆分"),
    ("visuals", "步骤4/7 视觉元素生成"),
    ("layout", "步骤5/7 四图排版"),
    ("manifest", "步骤6/7 整理与质检"),
    ("publish", "步骤7/7 发布（需用户确认）"),
]


def run_step(name: str, args_list: list, desc: str) -> int:
    """执行单个步骤，返回退出码。"""
    script_map = {
        "copy": "generate_copy.py",
        "structure": "structure_content.py",
        "split": "split_title.py",
        "visuals": "generate_visuals.py",
        "layout": "layout_images.py",
        "manifest": "build_manifest.py",
        "publish": "publish.py",
    }
    script = Path(__file__).resolve().parent / "scripts" / script_map[name]
    cmd = [sys.executable, str(script)] + args_list
    print(f"\n{'='*60}\n{desc}\n{'='*60}")
    result = subprocess.run(cmd, text=True)
    return result.returncode


def print_preview(out_dir: Path):
    """展示预览信息，等待用户确认。"""
    manifest_path = out_dir / "manifest.json"
    copy_path = out_dir / "publish-copy.txt"
    if not manifest_path.exists():
        print("[warn] 未找到 manifest.json，无法预览")
        return False

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"\n{'='*60}")
    print("📋 最终预览")
    print(f"{'='*60}")
    print(f"标题：{manifest.get('title', '')}")
    print(f"副标题：{manifest.get('subtitle', '')}")
    print(f"作者：{manifest.get('author', '')}")
    print(f"内容领域：{manifest.get('domain', '')}")
    print(f"\n话题标签：{' '.join('#'+t for t in manifest.get('hashtags', []))}")
    print(f"\n发布正文（前200字）：\n{manifest.get('note_body', '')[:200]}...")
    print(f"\n图片文件：")
    for page in manifest.get("pages", []):
        exists = "✓" if page.get("file_exists") else "✗"
        print(f"  {exists} {page.get('file', '')} ({page.get('role', '')})")
    print(f"\n文案文件：{copy_path}")
    print(f"清单文件：{manifest_path}")
    print(f"{'='*60}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="小红书一键生成图文并发布")
    parser.add_argument("--topic", required=True, help="主题或原始内容")
    parser.add_argument("--author", required=True, help="作者名")
    parser.add_argument("--audience", default="", help="目标人群")
    parser.add_argument("--tone", default="", help="语气要求")
    parser.add_argument("--visual-style", default="", help="视觉风格")
    parser.add_argument("--key-points", default="", help="必须体现的重点")
    parser.add_argument("--avoid", default="", help="禁止出现的内容")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR), help="输出目录")
    parser.add_argument("--resume-from", choices=[s[0] for s in STEP_ORDER], default="copy",
                        help="从指定步骤恢复执行")
    parser.add_argument("--dry-run", action="store_true", help="跳过真实 LLM 调用，使用 mock 数据")
    parser.add_argument("--no-publish", action="store_true", help="跳过发布步骤")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 从 --resume-from 开始执行
    start_idx = next(i for i, (n, _) in enumerate(STEP_ORDER) if n == args.resume_from)
    steps = STEP_ORDER[start_idx:]

    for name, desc in steps:
        if args.no_publish and name == "publish":
            print(f"\n跳过 {desc}")
            continue

        if name == "copy":
            rc = run_step(name, [
                "--topic", args.topic,
                "--author", args.author,
                "--audience", args.audience,
                "--tone", args.tone,
                "--visual-style", args.visual_style,
                "--key-points", args.key_points,
                "--avoid", args.avoid,
                "--output-dir", str(out_dir),
            ], desc)
        elif name == "publish":
            if not print_preview(out_dir):
                print("ERROR: 预览失败，终止流程", file=sys.stderr)
                return 1
            answer = input("\n是否确认发布？(y/N): ").strip().lower()
            if answer != "y":
                print("已取消发布。可手动使用 output/ 目录中的图片和 publish-copy.txt 进行发布。")
                return 0
            rc = run_step(name, ["--output-dir", str(out_dir), "--run"], desc)
        else:
            extra = []
            if name == "visuals" and args.dry_run:
                extra = ["--dry-run"]
            rc = run_step(name, ["--output-dir", str(out_dir)] + extra, desc)

        if rc != 0:
            print(f"\nERROR: {desc} 失败（退出码 {rc}），流程终止", file=sys.stderr)
            return rc

    print("\n✅ 全部步骤完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
