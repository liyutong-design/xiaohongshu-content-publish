# 小红书一键生成图文并发布 Skill

将原 Coze「小红书一键生成并发布图文工作流」转换为本地可运行的 Skill，实现从关键词输入到小红书发布的完整流程。

## 项目简介

本项目是一个 Python 脚本集合，通过调用 LLM（豆包）和图像生成 API（APIMart GPT-image-2），自动生成符合小红书平台规范的图文内容，包括：
- 1 张封面图 + 3 张内容页（共 4 张图片）
- 标题、正文、话题标签
- 半自动浏览器发布到小红书创作服务平台

## 功能介绍

| 功能 | 说明 |
|------|------|
| 文案生成 | 根据主题生成小红书风格标题、正文、话题标签 |
| 内容结构化 | 将文案拆分为 9 组小标题+正文，分配到 3 张内容页 |
| 标题语义拆分 | 将主标题拆分为两行，保持语义完整 |
| 视觉元素生成 | 生成 3 张素材图（主视觉 + 2 个辅助元素） |
| 图片排版 | 合成 1 封面 + 3 内容页，3:4 比例，统一风格 |
| 质量检查 | 验证字数、结构、图片完整性 |
| 半自动发布 | 自动上传图片、填写内容，人工确认发布 |

## 完整工作流程

```
关键词输入
    ↓
小红书文案生成（LLM）
    ↓
标题语义拆分（LLM + 规则校验）
    ↓
内容结构化拆分（LLM，9组内容）
    ↓
首页视觉元素拆分（LLM，3个元素）
    ↓
图片生成（APIMart GPT-image-2）
    ↓
图片排版（Pillow，1封面+3内容页）
    ↓
发布前质检（结构、字数、完整性）
    ↓
小红书半自动发布（Playwright + Edge）
    ↓
人工确认发布
```

## 项目目录结构

```
xiaohongshu-content-publish/
├── coze.txt                 # 原 Coze 工作流 JSON（参考）
├── coze工作流.md            # Coze 工作流文档
├── 小红书Skill方案.md        # Skill 设计方案
├── README.md                # 本文档
├── output/                  # 生成结果目录
│   ├── 01-cover.png         # 封面图
│   ├── 02-content-1.png     # 内容页1
│   ├── 03-content-2.png     # 内容页2
│   ├── 04-content-3.png     # 内容页3
│   ├── images/              # 原始素材图
│   ├── copy.json            # 文案数据
│   ├── structure.json       # 结构化内容
│   ├── split.json           # 标题拆分结果
│   ├── visuals.json         # 视觉元素数据
│   ├── manifest.json        # 四图清单（质检输入）
│   └── publish-copy.txt     # 发布用文案
└── trae/                    # Skill 核心代码
    ├── SKILL.md             # Skill 定义文档
    ├── main.py              # 主入口，串联 7 步流程
    ├── agents/
    │   └── openai.yaml      # 展示配置
    ├── assets/
    │   └── icon.svg         # Skill 图标
    ├── references/          # 规则文档
    │   ├── content-rules.md
    │   ├── visual-workflow.md
    │   ├── publishing-rules.md
    │   └── apimart-gpt-image-2.md
    └── scripts/             # 执行脚本
        ├── config.py        # 配置（密钥仅读环境变量）
        ├── llm_client.py    # LLM 客户端
        ├── generate_copy.py # 步骤1：文案生成
        ├── structure_content.py  # 步骤2：内容结构化
        ├── split_title.py   # 步骤3：标题语义拆分
        ├── generate_visuals.py   # 步骤4：图片生成
        ├── layout_images.py # 步骤5：图片排版
        ├── build_manifest.py     # 步骤6：整理与质检
        ├── publish.py       # 步骤7：半自动发布
        ├── validate_title.py     # 标题验证
        ├── validate_package.py   # 四图验证
        ├── apimart_gpt_image_2.py  # APIMart 生图调用
        └── prompts/         # 提示词模板（迁移自 Coze）
            ├── copy_prompt.py
            ├── structure_prompt.py
            ├── split_prompt.py
            └── element_prompt.py
```

## 环境要求

- Python 3.10+
- Microsoft Edge 浏览器（用于半自动发布）
- 网络连接（调用 LLM 和图像生成 API）

## 依赖安装

```bash
# 核心依赖
pip install pillow

# 发布功能依赖（可选，仅在需要自动发布时安装）
pip install playwright
playwright install chromium  # 或直接使用系统 Edge：channel="msedge"
```

## 环境变量配置说明

| 变量名 | 用途 | 必需 |
|--------|------|------|
| `DOUBAO_API_KEY` | 豆包 LLM API 密钥（用于文案生成、内容结构化、标题拆分） | 是 |
| `DOUBAO_BASE_URL` | 豆包 API 地址（默认火山引擎 ark） | 否 |
| `DOUBAO_MODEL` | 模型 ID（默认 doubao-pro-32k，可改为其他兼容模型） | 否 |
| `APIMART_API_KEY` | APIMart GPT-image-2 API 密钥（用于图片生成） | 是 |

**配置方式（Windows）：**

```powershell
# 用户级环境变量（永久）
[Environment]::SetEnvironmentVariable("DOUBAO_API_KEY", "你的密钥", "User")
[Environment]::SetEnvironmentVariable("APIMART_API_KEY", "你的密钥", "User")

# 当前会话临时设置
$env:DOUBAO_API_KEY = "你的密钥"
$env:APIMART_API_KEY = "你的密钥"
```

**重要：API 密钥仅通过环境变量读取，不要写入代码或任何文件。**

## 运行方法

### 完整流程（生成 + 发布）

```bash
cd trae
python main.py --topic "熬夜后如何快速恢复状态" --author "你的名字"
```

### 只生成不发布

```bash
python main.py --topic "..." --author "..." --no-publish
```

### 使用 Mock 数据测试（不调用真实 API）

```bash
python main.py --topic "..." --author "..." --dry-run
```

### 从某一步恢复执行

```bash
# 支持 copy/structure/split/visuals/layout/manifest/publish
python main.py --topic "..." --author "..." --resume-from layout
```

### 单独执行发布步骤

```bash
cd trae
python scripts/publish.py --run
```

## 生成结果说明

执行完成后，`output/` 目录包含：

| 文件 | 说明 |
|------|------|
| `01-cover.png` | 封面图（3:4，1242×1656） |
| `02-content-1.png` | 内容页1（第1-3组小标题+正文） |
| `03-content-2.png` | 内容页2（第4-6组小标题+正文） |
| `04-content-3.png` | 内容页3（第7-9组小标题+正文） |
| `manifest.json` | 四图清单（包含标题、正文、话题、图片路径） |
| `publish-copy.txt` | 发布用文案（标题+正文+话题标签） |
| `copy.json` | 原始文案数据 |
| `structure.json` | 结构化内容数据 |
| `split.json` | 标题拆分结果 |
| `visuals.json` | 视觉元素数据 |
| `images/` | 原始素材图目录 |

## 小红书半自动发布方法

1. 确保已安装 `playwright` 和系统 Edge 浏览器
2. 运行发布脚本：
   ```bash
   cd trae
   python scripts/publish.py --run
   ```
3. 浏览器自动打开小红书创作服务平台
4. 如需登录，扫码或手动登录
5. 脚本自动上传 4 张图片、填写标题、正文、话题标签
6. **人工检查内容无误后，手动点击「发布」按钮**
7. 按 Enter 键关闭浏览器

## 安全说明

- **API 密钥安全**：所有密钥仅通过环境变量读取，不写入代码或文件
- **原 Coze 密钥已作废**：原工作流中的发布插件密钥已移除（原值见 coze.txt）
- **浏览器安全**：使用 Playwright 启动系统 Edge，不存储账号密码，登录态保存在本地 User Data Dir
- **发布确认**：脚本不会自动点击「发布」按钮，需人工确认

## 已知限制

1. **Trae 沙盒限制**：浏览器自动化发布无法在 Trae 沙盒中运行，必须在本地终端执行
2. **发布按钮定位**：小红书页面结构可能变化，如找不到发布按钮，脚本会高亮显示可点击元素，请手动确认
3. **图片生成质量**：AI 生成图片可能需要人工筛选或多次生成
4. **文案质量**：LLM 生成内容建议人工审阅后再发布
5. **平台规则**：请遵守小红书社区规范，避免发布违规内容

## 与原 Coze 工作流的对应关系

| 原 Coze 节点 | Skill 实现 |
|-------------|-----------|
| 190438 小红书文案生成 | `scripts/generate_copy.py` + `prompts/copy_prompt.py` |
| 189374 元素成分 | `scripts/structure_content.py` + `prompts/structure_prompt.py` |
| 143075 首页文字拆分 | `scripts/split_title.py` + `prompts/split_prompt.py` |
| 115445/185636/141196 生图 | `scripts/generate_visuals.py` + `prompts/element_prompt.py` |
| 153832/129186/109747/116382 排版 | `scripts/layout_images.py`（Pillow） |
| 186516 图片整理 | `scripts/build_manifest.py` |
| 101779 shareToXiaohongshu | `scripts/publish.py`（Playwright） |

## 许可证

仅供学习和研究使用。
