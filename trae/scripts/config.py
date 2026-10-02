#!/usr/bin/env python3
"""Shared configuration. All secrets are read from environment variables only."""

import os
from pathlib import Path

# ---- paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent          # trae/
PROJECT_DIR = SKILL_DIR.parent         # repo root
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"

# ---- LLM (OpenAI-compatible chat completions, e.g. Doubao / 豆包) ----
# The original Coze workflow used 豆包·2.0·pro. Any OpenAI-compatible
# endpoint works. Configure via environment variables; never hardcode keys.
LLM_API_KEY_ENV = "DOUBAO_API_KEY"
LLM_BASE_URL_ENV = "DOUBAO_BASE_URL"
LLM_MODEL_ENV = "DOUBAO_MODEL"

DEFAULT_LLM_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_LLM_MODEL = "doubao-pro-32k"  # successor of 豆包·2.0·pro used in Coze

LLM_TIMEOUT = 300
LLM_MAX_TOKENS = 8192
LLM_TEMPERATURE = 0.7
# doubao-seed-2-1-lite 默认启用深度思考；纯文本生成任务按官方建议关闭，
# 与原 Coze 使用的豆包·2.0·pro（非思考模型）行为保持一致。
LLM_DISABLE_THINKING = True


def llm_settings() -> dict:
    """Return current LLM settings. api_key is None when not configured."""
    return {
        "api_key": os.environ.get(LLM_API_KEY_ENV),
        "base_url": os.environ.get(LLM_BASE_URL_ENV, DEFAULT_LLM_BASE_URL).rstrip("/"),
        "model": os.environ.get(LLM_MODEL_ENV, DEFAULT_LLM_MODEL),
    }


def llm_available() -> bool:
    return bool(os.environ.get(LLM_API_KEY_ENV))


# ---- image generation (APIMart GPT-image-2) ----
APIMART_KEY_ENV = "APIMART_API_KEY"


def image_gen_available() -> bool:
    return bool(os.environ.get(APIMART_KEY_ENV))


# ---- content contract (fixed by the original Coze workflow) ----
COVER_TITLE_MIN = 8    # 主标题 8-10 字（元素成分节点）
COVER_TITLE_MAX = 10
SUBTITLE_MIN = 15      # 副标题 15-20 字
SUBTITLE_MAX = 20
SECTION_COUNT = 9      # 9 个小标题 + 9 段正文
SECTION_BODY_MIN = 90
SECTION_BODY_MAX = 160
HASHTAG_MIN = 5
HASHTAG_MAX = 10
PAGE_ROLES = ["cover", "content-1", "content-2", "content-3"]
IMAGE_SIZE = "3:4"
IMAGE_RESOLUTION = "2k"
