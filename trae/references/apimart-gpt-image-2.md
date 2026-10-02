# APIMart GPT-image-2 接入规则

## 已确认接口

- 基础地址：`https://api.apimart.ai/v1`
- 提交生图：`POST /images/generations`
- 查询任务：`GET /tasks/{task_id}`
- 模型：`gpt-image-2`
- 鉴权：`Authorization: Bearer <API Key>`
- 密钥环境变量：`APIMART_API_KEY`

提交接口为异步模式。成功提交后，从 `data[0].task_id` 取得任务编号；轮询任务接口，直到状态变为 `completed` 或 `failed`。成功图片地址位于 `data.result.images[*].url[*]`。

## 基本参数

| 参数 | 用途 |
|---|---|
| `model` | 固定使用 `gpt-image-2` |
| `prompt` | 生图提示词 |
| `n` | 图片数量 |
| `size` | 图片比例，如 `3:4`、`1:1`、`16:9` |
| `resolution` | `1k`、`2k` 或 `4k` |
| `image_urls` | 可选参考图 URL 或 base64 data URI 数组 |

小红书竖版素材默认先使用 `3:4` 和 `2k`。如课堂模板规定其他比例，以模板为准。

## 调用方式

先检查请求，不访问网络：

```bash
python3 scripts/apimart_gpt_image_2.py \
  --prompt "主体明确、背景简洁的小红书视觉素材" \
  --size 3:4 --resolution 2k --dry-run
```

真实调用前，由用户在自己的运行环境中设置密钥。不要把密钥写入脚本、Skill、作业文件或聊天记录。

```bash
python3 scripts/apimart_gpt_image_2.py \
  --prompt "主体明确、背景简洁的小红书视觉素材" \
  --size 3:4 --resolution 2k
```

脚本输出任务状态和最终图片 URL，不声称完成下载或排版。

## 失败处理

- `400`：检查比例、分辨率和提示词等参数。
- `401`：检查本地环境变量中的密钥，不在聊天中索要密钥。
- `402`：提示账户余额不足。
- `429`：稍后重试，避免连续高频请求。
- `500`、`503` 或任务 `failed`：保留提示词，标记为待生成；不要重做文案。
- 超过等待时间：保留 `task_id`，报告任务仍未得到最终结果。

只依据接口的真实响应报告状态。
