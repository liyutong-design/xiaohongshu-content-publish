# -*- coding: utf-8 -*-
"""首页视觉元素生图提示词。

沿用原 Coze 图片生成节点（115445 / 185636 / 141196）的提示词模板：
「1个{{名词}}，简单插画，卡通风格，纯白色背景」（主题元素额外带「儿童简笔画」）。
在此之上补充 Skill 方案步骤4 要求的完整要素
（主体、构图、风格、色彩、光线、背景、用途、3:4 画幅），
并保持「纯白色背景」以便后续抠图。
"""

MAIN_IMAGE_TEMPLATE = (
    "1个{name}，简单插画，卡通风格，儿童简笔画，纯白色背景。"
    "主体居中，构图饱满，线条简洁，色彩明快柔和，光线均匀，"
    "用于小红书四图笔记封面主视觉，3:4竖版画幅，画面中不要出现任何文字。"
)

ELEMENT_IMAGE_TEMPLATE = (
    "1个{name}，简单插画，卡通风格，纯白色背景。"
    "主体居中，构图简洁，色彩与主视觉统一，光线均匀，"
    "用于小红书四图笔记封面辅助装饰元素，3:4竖版画幅，画面中不要出现任何文字。"
)


def build_image_prompts(structured: dict) -> dict:
    """根据结构化结果生成三个视觉元素的生图提示词。"""
    prompts = {}
    main_name = (structured.get("main_image") or "").strip()
    el1 = (structured.get("element_img1") or "").strip()
    el2 = (structured.get("element_img2") or "").strip()
    if main_name:
        prompts["main_image"] = MAIN_IMAGE_TEMPLATE.format(name=main_name)
    if el1:
        prompts["element_img1"] = ELEMENT_IMAGE_TEMPLATE.format(name=el1)
    if el2:
        prompts["element_img2"] = ELEMENT_IMAGE_TEMPLATE.format(name=el2)
    return prompts
