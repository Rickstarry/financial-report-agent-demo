"""模型调用模块:报表定位 -> 提示词组装 -> DeepSeek -> JSON 结果。"""

import json
import logging
import os
import re
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "src" / "prompts"


def parse_json_answer(answer: str):
    """容错解析模型输出:容忍 ```json 围栏与前后解释文字。"""
    text = answer.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {"raw": answer}


def find_statement_start(text: str) -> int:
    for anchor in ("合并及公司资产负债表", "合并资产负债表"):
        idx = text.find(anchor, 90000)
        if idx >= 0:
            return idx
    idx = text.find("资产负债表", 90000)
    return idx if idx >= 0 else 90000


def load_prompts():
    system = (PROMPT_DIR / "analysis_system.txt").read_text(encoding="utf-8")
    user_tpl = (PROMPT_DIR / "analysis_user.txt").read_text(encoding="utf-8")
    return system, user_tpl


def analyze_txt(
    txt: Path,
    chars: int = 14000,
    out: Path | None = None,
    log: logging.Logger | None = None,
) -> dict:
    log = log or logging.getLogger("bisaienv")
    text = txt.read_text(encoding="utf-8")
    start = find_statement_start(text)
    page_marker = text.rfind("\n===== 第", 0, start)
    if page_marker >= 0:
        start = page_marker + 1
    excerpt = text[start : start + chars]
    log.info("已定位报表起点(第 %d 字符),截取 %d 字符", start, len(excerpt))

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key == "sk-你的DeepSeek密钥":
        raise SystemExit("请先在 .env 配置 DEEPSEEK_API_KEY")

    system_prompt, user_tpl = load_prompts()
    user_prompt = user_tpl.replace("{{REPORT_NAME}}", txt.stem).replace("{{EXCERPT}}", excerpt)

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    log.info("调用模型:%s", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    resp = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    usage = getattr(resp, "usage", None)
    if usage:
        log.info("Token 用量:输入 %s,输出 %s", usage.prompt_tokens, usage.completion_tokens)

    answer = resp.choices[0].message.content
    data = parse_json_answer(answer)

    result = {
        "source_txt": str(txt),
        "excerpt_start": start,
        "excerpt_chars": len(excerpt),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
        if usage
        else None,
        "analysis": data,
    }

    if out is None:
        out = txt.with_name(f"{txt.stem}-结构解析结果.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("结果已保存:%s", out)
    return result


def pretty_print(result: dict) -> None:
    print("\n=== 分析结果概要 ===")
    analysis = result.get("analysis", {})
    if "raw" in analysis:
        print(analysis["raw"][:2000])
        return
    for st in analysis.get("statements", []):
        name = st.get("name", "")
        totals = st.get("key_totals", {})
        print(f"- {name}: {totals}")
    print("置信度:", analysis.get("confidence"))
    print("理由:", analysis.get("reason"))
    print("\n完整 JSON 已保存。")
