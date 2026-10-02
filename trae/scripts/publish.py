#!/usr/bin/env python3
"""步骤7：小红书发布（半自动浏览器发布）。

对应原 Coze 节点 101779「shareToXiaohongshu」。原插件为"小红书发布_智界小红书分享"
（原 API Key 已作废，不再使用，具体值见 coze.txt）。

替代方案：Playwright 模拟浏览器打开小红书创作服务平台 (creator.xiaohongshu.com)，
在已登录窗口中自动填入标题、正文、上传四图并添加话题标签。

安全设计：
- 不存储账号密码；
- 首次运行时通过二维码/浏览器已有登录态登录；
- 登录态以浏览器 User Data Directory 方式保留，不提取 Cookie；
- 发布失败后保留全部素材，不重新生成内容。

依赖：playwright（pip install playwright && playwright install chromium）。
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

sync_playwright = None  # 延迟导入，dry-run 模式不需要 playwright

XHS_CREATOR_URL = "https://creator.xiaohongshu.com/publish/publish"
HEADLESS = False  # 半自动：需要用户可见浏览器
USER_DATA_DIR = Path.home() / ".trae-xiaohongshu-profile"
PUBLISH_TIMEOUT = 120  # 秒


def ensure_logged_in(page, playwright, work_dir) -> bool:
    """判断创作平台是否已登录；未登录时等待用户扫码。"""
    page.goto(XHS_CREATOR_URL, wait_until="domcontentloaded")
    time.sleep(2)
    # 小红书创作平台未登录时会重定向到登录页或出现登录弹窗
    if "/login" in page.url or page.is_visible("[placeholder=\"手机号\"]", timeout=2000):
        print("[info] 检测到未登录，请在小红书创作服务平台扫码登录")
        print("[info] 登录完成后，在命令行中创建文件 xhs_login_done 继续：")
        print(f"       New-Item -ItemType File -Path {work_dir / 'xhs_login_done'}")
        flag = work_dir / "xhs_login_done"
        flag.unlink(missing_ok=True)
        while not flag.exists():
            time.sleep(3)
        page.goto(XHS_CREATOR_URL, wait_until="domcontentloaded")
        time.sleep(2)
    return "/login" not in page.url and not page.is_visible("[placeholder=\"手机号\"]", timeout=2000)


def ensure_edit_mode(page) -> bool:
    """确保页面已进入编辑模式（显示标题/正文输入框和发布按钮）。"""
    try:
        # 检查是否已有标题输入框
        title_input = page.locator("input[placeholder*='标题'], input[placeholder*='填写标题']").first
        if title_input.count() > 0:
            print("[info] 页面已进入编辑模式")
            return True
        
        print("[info] 页面未进入编辑模式，尝试切换Tab刷新...")
        
        # 尝试点击「上传图文」Tab 强制刷新
        tab = page.locator("div.creator-tab > span.title:has-text('上传图文')").first
        if tab.count() > 0:
            tab.click()
            time.sleep(3)
            
            # 再次检查
            title_input = page.locator("input[placeholder*='标题'], input[placeholder*='填写标题']").first
            if title_input.count() > 0:
                print("[info] 切换Tab后进入编辑模式")
                return True
        
        # 尝试触发 input 事件强制页面重新渲染
        page.evaluate("""() => {
            const event = new Event('input', { bubbles: true });
            document.body.dispatchEvent(event);
        }""")
        time.sleep(2)
        
        title_input = page.locator("input[placeholder*='标题'], input[placeholder*='填写标题']").first
        if title_input.count() > 0:
            print("[info] 触发事件后进入编辑模式")
            return True
            
        print("[warn] 无法进入编辑模式")
        return False
    except Exception as exc:
        print(f"[warn] 确保编辑模式时出错：{exc}")
        return False


def upload_images(page, image_paths: list) -> bool:
    """上传四张图片到图文发布页。"""
    try:
        # 切换到图文发布 Tab（避免点到隐藏的占位元素）
        tab = page.locator("div.creator-tab.active > span.title:has-text('上传图文')").first
        if tab.is_visible(timeout=3000):
            tab.click()
        else:
            # 备选：通过 evaluate 直接点击可见的 tab
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('div.creator-tab');
                for (const t of tabs) {
                    if (t.textContent.includes('上传图文') && t.offsetParent !== null) {
                        t.click();
                        break;
                    }
                }
            }""")
        time.sleep(2)

        # 文件上传 input（已确认选择器：input.upload-input）
        # 使用 set_input_files 直接传入文件路径，不操作 Windows 文件选择窗口
        upload_input = page.locator("input.upload-input").first
        
        # 检查 input 是否存在（可能隐藏）
        if upload_input.count() == 0:
            print("[warn] 未找到文件上传 input 元素", file=sys.stderr)
            return False
            
        # 直接设置文件，无需点击（支持隐藏 input）
        upload_input.set_input_files(image_paths)
        print(f"[info] 已上传 {len(image_paths)} 张图片")
        
        # 等待图片上传完成、表单渲染
        time.sleep(5)
        
        # 确保进入编辑模式
        if not ensure_edit_mode(page):
            print("[warn] 无法进入编辑模式，发布按钮可能不显示")
            return False
        
        print("[info] 图片上传成功，已进入编辑模式")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 图片上传失败：{exc}", file=sys.stderr)
        return False


def fill_title(page, title: str) -> bool:
    try:
        # 标题输入框在图片上传后才渲染，尝试多种选择器
        selectors = [
            "div.upload-content input[type='text']",
            "input[placeholder*='标题']",
            "input[placeholder*='填写标题']",
            ".title-input input",
            "input[type='text']"
        ]
        
        for selector in selectors:
            title_input = page.locator(selector).first
            if title_input.count() > 0:
                title_input.fill(title)
                print(f"[info] 标题已填入（选择器: {selector}）")
                return True
        
        print("[warn] 未找到标题输入框", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 标题填写失败：{exc}", file=sys.stderr)
        return False


def fill_body(page, body: str) -> bool:
    try:
        # 正文区域在图片上传后才渲染，尝试多种选择器
        selectors = [
            "div.upload-content [contenteditable='true']",
            "div.upload-content textarea",
            "textarea[placeholder*='正文']",
            "textarea[placeholder*='内容']",
            ".ql-editor",
            "[contenteditable='true']"
        ]
        
        for selector in selectors:
            body_input = page.locator(selector).first
            if body_input.count() > 0:
                body_input.fill(body)
                print(f"[info] 正文已填入（选择器: {selector}）")
                return True
        
        print("[warn] 未找到正文输入框", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 正文填写失败：{exc}", file=sys.stderr)
        return False


def add_hashtags(page, hashtags: list) -> bool:
    """在正文末尾添加话题标签（以 #话题 形式插入）。"""
    try:
        tags_text = " " + " ".join("#" + t for t in hashtags)
        
        # 尝试多种选择器找到正文区域
        selectors = [
            "div.upload-content [contenteditable='true']",
            "div.upload-content textarea",
            "textarea[placeholder*='正文']",
            "textarea[placeholder*='内容']",
            ".ql-editor",
            "[contenteditable='true']"
        ]
        
        for selector in selectors:
            body_input = page.locator(selector).first
            if body_input.count() > 0:
                body_input.click()
                page.keyboard.press("End")
                body_input.type(tags_text)
                print(f"[info] 话题标签已添加（选择器: {selector}）")
                return True
        
        print("[warn] 未找到话题标签输入框", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 话题标签添加失败：{exc}", file=sys.stderr)
        return False


def find_publish_button(page) -> bool:
    """滚动到页面底部并查找发布按钮。"""
    try:
        # 滚动到页面底部
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        # 尝试多种选择器查找发布按钮
        selectors = [
            'button:has-text("发布")',
            'button[class*="publish"]',
            'button[class*="submit"]',
            'div[class*="publish"]',
            '[class*="publish-btn"]',
            '[class*="submit-btn"]',
            'button[type="submit"]',
            '//button[contains(., "发布")]'  # xpath
        ]
        
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.count() > 0 and btn.is_visible(timeout=2000):
                    # 高亮显示按钮（添加红色边框）
                    btn.evaluate("el => { el.style.border = '3px solid red'; el.style.background = 'yellow'; }")
                    print(f"[info] 已找到并高亮发布按钮（选择器: {selector}），请滚动查看")
                    return True
            except Exception:
                continue
        
        print("[warn] 未找到发布按钮，可能需要手动查找")
        return False
    except Exception as exc:
        print(f"[warn] 查找发布按钮时出错：{exc}")
        return False


def do_publish(manifest: dict, image_dir: Path, dry_run: bool = True) -> dict:
    """执行浏览器发布。dry_run=True 时只填内容不点发布按钮。"""
    image_order = ["01-cover.png", "02-content-1.png", "03-content-2.png", "04-content-3.png"]
    image_paths = [str(image_dir / f) for f in image_order]
    missing = [p for p in image_paths if not Path(p).exists()]
    if missing:
        return {"status": "failed", "error": f"缺少图片文件：{missing}"}

    title = manifest.get("title", "")
    body = manifest.get("note_body", "")
    hashtags = manifest.get("hashtags", [])

    if dry_run:
        print("[info] DRY-RUN 模式：仅展示发布内容，不打开浏览器")
        return {
            "status": "dry_run",
            "title": title,
            "body_preview": body[:200] + ("..." if len(body) > 200 else ""),
            "hashtags": hashtags,
            "images": image_paths,
        }

    global sync_playwright
    try:
        from playwright.sync_api import sync_playwright as _sp
        sync_playwright = _sp
    except ImportError:
        return {"status": "failed",
                "error": "缺少 playwright，请先执行 pip install playwright && playwright install chromium"}

    with sync_playwright() as p:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        # 使用系统自带 Microsoft Edge，无需下载 Chromium
        browser = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=HEADLESS,
            channel="msedge",
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = browser.new_page()
        work_dir = Path(image_dir).parent
        if not ensure_logged_in(page, p, work_dir):
            return {"status": "failed", "error": "登录小红书创作平台失败"}

        ok = True
        ok &= upload_images(page, image_paths)
        ok &= fill_title(page, title)
        ok &= fill_body(page, body)
        ok &= add_hashtags(page, hashtags)

        if not ok:
            print("[warn] 部分内容填写失败，请手动检查浏览器")

        # 查找并高亮发布按钮
        if find_publish_button(page):
            print("[info] 发布按钮已找到并高亮显示")
        else:
            print("[warn] 发布按钮未找到，可能原因：")
            print("  1. 页面未完全进入编辑模式")
            print("  2. 浏览器窗口太小，需要最大化")
            print("  3. 需要滚动到页面底部")
            print("[info] 请手动检查页面底部或右侧是否有发布按钮")
        
        print("[info] 内容已填入创作平台，请确认后手动点击「发布」")
        print("[info] 浏览器窗口将保持打开，完成后请手动关闭浏览器")
        # 不关闭浏览器，保持窗口打开等待用户手动确认
        input("[info] 按 Enter 键关闭浏览器并结束脚本...")
        browser.close()
        return {"status": "ok", "message": "已填入创作平台，请检查是否成功发布"}


def main() -> int:
    parser = argparse.ArgumentParser(description="小红书图文半自动发布")
    parser.add_argument("--manifest", default="", help="manifest.json 路径")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run", action="store_true", help="真正打开浏览器并填入内容（默认 dry-run）")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest) if args.manifest else out_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: 找不到 {manifest_path}，请先完成前序步骤", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = do_publish(manifest, out_dir, dry_run=not args.run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("ok", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
