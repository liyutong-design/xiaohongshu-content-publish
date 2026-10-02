#!/usr/bin/env python3
"""步骤4：首页视觉元素拆分与图片素材生成。

对应 Coze 节点 115445 / 185636 / 141196（图片生成）。
- 依据 structure.json 中的 main_image / element_img1 / element_img2 生成提示词；
- 优先调用 scripts/apimart_gpt_image_2.py（密钥仅来自环境变量 APIMART_API_KEY）；
- 单张图片失败只重试该图；接口不可用时保留提示词并标记「待生成」；
- 结果写入 output/visuals.json。
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from prompts.element_prompt import build_image_prompts

SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_SCRIPT = SCRIPT_DIR / "apimart_gpt_image_2.py"

ELEMENT_KEYS = ("main_image", "element_img1", "element_img2")


def _last_json_object(text: str):
    """依次解析文本中所有完整 JSON 对象，返回最后一个（生图脚本会先后输出 submitted 和最终状态）。"""
    decoder = json.JSONDecoder()
    idx = text.find("{")
    last = None
    while idx != -1:
        try:
            obj, end = decoder.raw_decode(text, idx)
            last = obj
            idx = text.find("{", end)
        except json.JSONDecodeError:
            idx = text.find("{", idx + 1)
    return last


def generate_one(prompt: str, size: str, resolution: str) -> dict:
    """调用 GPT-image-2 生成单张图片。返回 {status, image_url|task_id|error}。"""
    cmd = [sys.executable, str(IMAGE_SCRIPT), "--prompt", prompt,
           "--size", size, "--resolution", resolution]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
    if result.returncode != 0:
        return {"status": "failed", "error": (result.stderr or result.stdout).strip()[:500]}
    # 从输出中提取最后一个完整 JSON 对象（脚本先输出 submitted 单行，再输出多行最终状态）
    status = _last_json_object(result.stdout)
    if status is None:
        return {"status": "failed", "error": "image script returned no JSON status"}
    if status.get("status") == "completed" and status.get("image_urls"):
        return {"status": "completed", "image_url": status["image_urls"][0],
                "task_id": status.get("task_id")}
    return {"status": status.get("status", "failed"), "task_id": status.get("task_id"),
            "error": status.get("error", "")}


def download_image(url: str, dest: Path) -> bool:
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as exc:  # noqa: BLE001 - 保留真实错误
        llm_warn = f"下载图片失败 {url}: {exc}"
        print(f"[warn] {llm_warn}", file=sys.stderr)
        return False


def generate_visuals(structure: dict, out_dir: Path, dry_run: bool = False) -> dict:
    prompts = build_image_prompts(structure)
    visuals = {"elements": {}, "size": config.IMAGE_SIZE, "resolution": config.IMAGE_RESOLUTION}
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    for key in ELEMENT_KEYS:
        name = (structure.get(key) or "").strip()
        prompt = prompts.get(key, "")
        entry = {"name": name, "prompt": prompt, "status": "pending"}
        if not prompt:
            entry["status"] = "missing"
            visuals["elements"][key] = entry
            continue

        if dry_run or not config.image_gen_available():
            entry["status"] = "待生成"
            if not config.image_gen_available():
                entry["reason"] = f"环境变量 {config.APIMART_KEY_ENV} 未配置"
            visuals["elements"][key] = entry
            continue

        result = generate_one(prompt, config.IMAGE_SIZE, config.IMAGE_RESOLUTION)
        entry.update(result)
        if result.get("status") == "completed" and result.get("image_url"):
            local = img_dir / f"{key}.png"
            if download_image(result["image_url"], local):
                entry["local_file"] = str(local)
        visuals["elements"][key] = entry
        time.sleep(1)  # 避免高频请求

    return visuals


def main() -> int:
    parser = argparse.ArgumentParser(description="生成三个视觉元素素材（主视觉+两个辅助元素）")
    parser.add_argument("--structure", default="", help="structure.json 路径")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dry-run", action="store_true", help="只输出提示词，不调用生图接口")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    structure_path = Path(args.structure) if args.structure else out_dir / "structure.json"
    if not structure_path.exists():
        print(f"ERROR: 找不到 {structure_path}，请先运行 structure_content.py", file=sys.stderr)
        return 2
    structure = json.loads(structure_path.read_text(encoding="utf-8"))

    visuals = generate_visuals(structure, out_dir, dry_run=args.dry_run)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "visuals.json"
    out_file.write_text(json.dumps(visuals, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {k: v.get("status") for k, v in visuals["elements"].items()}
    print(json.dumps({"status": "ok", "file": str(out_file), "elements": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
