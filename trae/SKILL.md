---
name: xiaohongshu-content-publish
description: Create a four-image Xiaohongshu post from a topic and author name, including domain-aware copy, a cover, three structured content pages, visual prompts, quality checks, user approval, and truthful publish handoff. Use when a user asks to generate, revise, prepare, or publish a Xiaohongshu graphic post; do not use for video posts or unrelated single-image generation.
---

# 小红书一键生成图文并发布

把主题转化为一套可检查的小红书四图笔记。始终先生成和验证内容，再向用户展示预览；只有用户明确确认后，才尝试调用真实可用的发布工具。

## 执行入口

完整流程由 `main.py` 串联，各步骤脚本位于 `scripts/`：

```bash
# 完整流程（文案→结构化→拆分→生图→排版→质检→确认后发布）
python main.py --topic "大学生熬夜自救" --author "李悦彤"

# 只生成不发布
python main.py --topic "..." --author "..." --no-publish

# 生图步骤只出提示词（不调用接口）
python main.py --topic "..." --author "..." --dry-run

# 从某一步恢复（copy/structure/split/visuals/layout/manifest/publish）
python main.py --topic "..." --author "..." --resume-from layout
```

环境变量（只在运行环境中配置，禁止写入任何文件）：

| 变量 | 用途 |
| --- | --- |
| `DOUBAO_API_KEY` | 文案/结构化/标题拆分的 LLM 密钥（OpenAI 兼容接口） |
| `DOUBAO_BASE_URL` | 可选，默认火山引擎 ark 地址 |
| `DOUBAO_MODEL` | 可选，默认 doubao-pro-32k（对应原 Coze 豆包·2.0·pro） |
| `APIMART_API_KEY` | GPT-image-2 生图密钥 |

脚本与提示词文件职责：

| 文件 | 对应 Coze 节点 | 作用 |
| --- | --- | --- |
| `scripts/prompts/copy_prompt.py` | 190438 小红书文案生成 | 完整迁移原 systemPrompt |
| `scripts/prompts/structure_prompt.py` | 189374 元素成分 | 迁移并改为通用领域（原写死养生） |
| `scripts/prompts/split_prompt.py` | 143075 首页文字拆分 | 完整迁移原 systemPrompt |
| `scripts/prompts/element_prompt.py` | 115445/185636/141196 生图 | 沿用「简单插画，卡通风格，纯白色背景」模板 |
| `scripts/generate_copy.py` | 190438 | 生成标题、正文、话题标签 → copy.json |
| `scripts/structure_content.py` | 189374 | 9组结构化拆分 + 局部重试 → structure.json |
| `scripts/split_title.py` | 143075 | 语义拆分 + validate_title.py 校验 → split.json |
| `scripts/generate_visuals.py` | 115445/185636/141196 | 三元素生图 → visuals.json + images/ |
| `scripts/layout_images.py` | 153832/129186/109747/116382 + 抠图节点 | 近白抠图 + 封面与三内容页排版（Pillow） |
| `scripts/build_manifest.py` | 186516 图片整理 | 生成 manifest.json / publish-copy.txt 并质检 |
| `scripts/publish.py` | 101779 shareToXiaohongshu | Playwright 半自动发布到创作服务平台 |
| `scripts/config.py` | — | 路径与模型配置，密钥仅读环境变量 |
| `scripts/llm_client.py` | — | OpenAI 兼容 chat 客户端（stdlib） |

## 开始前

1. 获取主题和作者名。缺少任意一项时先询问。
2. 接收可选信息：目标受众、重点、参考资料、参考图片、语气、视觉风格、必须保留和禁止出现的内容。
3. 不补写用户未提供的真实经历、价格、地址、疗效或数据。
4. 读取 [references/content-rules.md](references/content-rules.md) 生成内容。
5. 需要生成或处理图片时，读取 [references/visual-workflow.md](references/visual-workflow.md)。
6. 使用 APIMart 的 GPT-image-2 时，读取 [references/apimart-gpt-image-2.md](references/apimart-gpt-image-2.md)。
7. 进入确认或发布阶段时，读取 [references/publishing-rules.md](references/publishing-rules.md)。

## 工作流

### 1. 识别领域

根据主题判断美妆、穿搭、美食、旅行、养生、电商、校园、作品展示或其他领域。无法可靠判断时询问用户，不用单个关键词机械分类。

### 2. 生成并结构化文案

生成一个完整主标题、必要的副标题、三个页面标题、九个小标题、九段正文、五至十个相关话题标签和发布正文。把九组内容按递进关系分配到三张内容页，每页三组。遵守内容规则，避免重复。

### 3. 拆分标题

在自然语义停顿处把完整主标题拆成两行。运行：

```bash
python3 scripts/validate_title.py --original "完整标题" --line1 "第一行" --line2 "第二行"
```

验证失败时重新拆分，禁止通过修改原标题来通过检查。

### 4. 规划并生成视觉素材

提取一个主体元素和两个辅助元素。为每个元素生成包含主体、构图、风格、色彩、光线、背景和用途的提示词。

优先使用已配置的 APIMart GPT-image-2 调用脚本。先用 `--dry-run` 检查请求；只有环境变量 `APIMART_API_KEY` 已由用户在其运行环境中配置时，才允许真实调用。没有密钥或调用失败时，输出提示词并将图片状态标记为“待生成”，不得索要用户在聊天中粘贴密钥。

```bash
python3 scripts/apimart_gpt_image_2.py --prompt "图片提示词" --size 3:4 --resolution 2k --dry-run
```

### 5. 抠图与排版

仅在存在真实抠图和画板工具或模板时执行：去除主体背景；制作一张首页；制作三张内容页；保持四张图的系列感，避免文字裁切、重叠或被素材遮挡。缺少工具或模板时，交付逐页排版说明，不宣称图片已经完成。

### 6. 整理和验证四图

按 `cover`、`content-1`、`content-2`、`content-3` 顺序整理。将最终数据写入 JSON 清单并运行：

```bash
python3 scripts/validate_package.py manifest.json
```

根据报告修复标题、字数、数量或顺序问题。视觉质量仍需人工或具备看图能力的模型检查。

### 7. 展示并等待确认

向用户展示或列出四张图片及其真实状态、发布标题、发布正文、话题标签和检查结果。明确询问是否确认发布。用户要求修改时只返回相应环节；没有明确确认时停止在预览阶段。

### 8. 发布或交付

仅在环境中存在已授权、真实可用的发布工具时调用。返回工具给出的真实结果。若工具不存在或发布失败，保留四图、标题、正文和标签，说明真实状态，并提供手动发布材料。不得虚构发布成功，也不得因发布失败重做全部内容。

## 局部重试

定位失败环节，只重试该环节：文案失败重做文案；单张图片失败重做该图；抠图失败重做抠图；单页排版失败重做该页；发布失败转为手动发布。

## 完成条件

- 固定一张首页和三张内容页；
- 标题两行合并后与原标题完全一致；
- 三页共九个小标题和九段正文，每段 90–160 个 Unicode 字符；
- 图片顺序正确，内容与主题一致，版式可读；
- 已展示最终预览并获得明确确认后才尝试发布；
- 所有工具调用和结果均为真实状态。
