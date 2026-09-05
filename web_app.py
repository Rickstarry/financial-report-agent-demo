"""金融研报智能体 - Web 演示界面。

启动:
    .venv\\Scripts\\activate
    streamlit run web_app.py

浏览器访问 http://localhost:8501
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src import analyzer, logger, parser

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
LOG_DIR = ROOT / "logs"

load_dotenv(ROOT / ".env")

st.set_page_config(page_title="金融研报智能体", page_icon="📊", layout="wide")

st.title("📊 金融研报智能体 · 财报结构解析")
st.caption("本地可运行原型:PDF 解析 → 报表定位 → DeepSeek 结构化分析(依赖配置在 .env)")

with st.sidebar:
    st.subheader("⚙️ 参数设置")
    chars = st.slider("截取字符数(控制 token 成本)", 5000, 40000, 14000, step=1000)
    st.caption("提示指令见 src/prompts/,日志输出到 logs/")
    if st.button("查看最近日志"):
        logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            st.code(logs[0].read_text(encoding="utf-8")[-2500:], language="text")
        else:
            st.info("还没有日志")


def run_analysis(pdf_path: Path, name: str, chars: int):
    log = logger.setup_logger(LOG_DIR)
    log.info("Web 任务开始:%s", name)
    progress = st.progress(0, text="开始解析 PDF…")

    pdf_path = Path(pdf_path)
    text = parser.extract_pdf_text(pdf_path)
    txt_path = DATA_DIR / f"{pdf_path.stem}.txt"
    txt_path.write_text(text, encoding="utf-8")
    heads = parser.detect_headings(text)
    progress.progress(45, text=f"解析完成:{len(text)} 字符,正在调用模型…")
    log.info("抽取字符数:%d,疑似章节标题:%d", len(text), len(heads))

    out_json = DATA_DIR / f"{pdf_path.stem}-结构解析结果.json"
    result = analyzer.analyze_txt(txt_path, chars=chars, out=out_json, log=log)
    progress.progress(100, text="完成")
    return result, txt_path, out_json


def render_result(result: dict):
    analysis = result.get("analysis", {})
    if "raw" in analysis:
        st.error("模型未返回标准 JSON(可能被截断),可尝试增大截取字符数或重试。")
        st.code(analysis["raw"], language="json")
        return

    st.subheader("📈 识别结果")
    st.write(f"置信度:**{analysis.get('confidence', 'N/A')}**")
    st.write(analysis.get("reason", ""))

    for stmt in analysis.get("statements", []):
        with st.expander(f"📄 {stmt.get('name', '未命名')}", expanded=True):
            st.write(f"**期间:** {stmt.get('period', '-')}")
            totals = stmt.get("key_totals", {})
            if totals:
                cols = st.columns(min(len(totals), 4))
                for i, (k, v) in enumerate(totals.items()):
                    cols[i % 4].metric(k, str(v))
            items = stmt.get("main_items", [])
            if items:
                st.write("**主要项目:**" + " · ".join(str(x) for x in items[:25]))
            issues = stmt.get("quality_issues", [])
            if issues:
                st.warning("疑似错位/乱码/缺列(赛题 E 场景):")
                for issue in issues:
                    st.markdown(f"- {issue}")


mode = st.radio("选择数据来源", ["上传财报 PDF", "使用内置样例(美的集团)"], horizontal=True)

uploaded = None
if mode == "上传财报 PDF":
    uploaded = st.file_uploader("上传 PDF(最大 100MB)", type=["pdf"])
    if uploaded:
        st.info(f"已选择:{uploaded.name} ({uploaded.size / 1024 / 1024:.1f} MB)")
else:
    sample = DATA_DIR / "美的集团-2026年半年度报告.pdf"
    st.info(f"内置样例:{sample.name}")

if st.button("🚀 一键解析并分析", type="primary", disabled=(mode == "上传财报 PDF" and uploaded is None)):
    try:
        if mode == "上传财报 PDF":
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            target = UPLOAD_DIR / Path(uploaded.name).name
            target.write_bytes(uploaded.getbuffer())
            pdf_path = target
            name = uploaded.name
        else:
            pdf_path = sample
            name = sample.name

        with st.spinner("正在运行(解析约 10-20 秒,模型调用约 10 秒)…"):
            result, txt_path, out_json = run_analysis(pdf_path, name, chars)

        st.success(f"完成!结果已保存:{out_json.name}")
        render_result(result)

        with st.expander("查看中间文本"):
            text = txt_path.read_text(encoding="utf-8")
            st.write(f"共 {len(text)} 字符")
            st.code(text[:1500], language="text")
    except Exception as e:
        st.error(f"运行出错:{e}")
        log = logger.setup_logger(LOG_DIR)
        log.error("Web 任务失败:%s", e, exc_info=True)

st.divider()
st.caption("竞赛定位:本地可运行原型 · 数据处理 src/parser.py · 模型调用 src/analyzer.py · 提示指令 src/prompts/ · 日志 logs/")
