"""金融研报智能体 - 本地可运行入口(决赛交付形态)。

用法:
    python run.py parse --pdf data\\xxx.pdf [--out data\\xxx.txt]
    python run.py analyze --txt data\\xxx.txt [--chars 14000] [--out data\\result.json]
    python run.py pipeline --pdf data\\xxx.pdf [--chars 14000] [--out data\\result.json]

流程:PDF -> 文本 -> 报表定位 -> DeepSeek 结构化分析 -> JSON,全程写日志。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src import analyzer, logger, parser

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="本地金融研报智能体")
    sub = p.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="PDF -> 文本")
    p_parse.add_argument("--pdf", type=Path, required=True)
    p_parse.add_argument("--out", type=Path, default=None)

    p_analyze = sub.add_parser("analyze", help="文本 -> DeepSeek 结构化分析")
    p_analyze.add_argument("--txt", type=Path, required=True)
    p_analyze.add_argument("--chars", type=int, default=14000)
    p_analyze.add_argument("--out", type=Path, default=None)

    p_pipe = sub.add_parser("pipeline", help="一键:PDF -> 文本 -> 分析 -> JSON")
    p_pipe.add_argument("--pdf", type=Path, required=True)
    p_pipe.add_argument("--txt", type=Path, default=None)
    p_pipe.add_argument("--chars", type=int, default=14000)
    p_pipe.add_argument("--out", type=Path, default=None)
    return p.parse_args()


def resolve_path(path: Path | None, default: Path) -> Path:
    p = path if path is not None else default
    return p if p.is_absolute() else (ROOT / p)


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    log = logger.setup_logger(LOG_DIR)
    log.info("===== 任务开始:%s =====", args.command)

    if args.command == "parse":
        pdf = resolve_path(args.pdf, Path())
        out = resolve_path(args.out, DATA_DIR / f"{pdf.stem}.txt")
        log.info("解析 PDF:%s", pdf)
        text = parser.extract_pdf_text(pdf)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        heads = parser.detect_headings(text)
        log.info("抽取字符数:%d,疑似章节标题:%d", len(text), len(heads))
        log.info("文本已保存:%s", out)
        print(f"\n解析完成:{out}")

    elif args.command == "analyze":
        txt = resolve_path(args.txt, Path())
        out = resolve_path(args.out, DATA_DIR / f"{txt.stem}-结构解析结果.json")
        log.info("开始分析:%s(chars=%d)", txt, args.chars)
        result = analyzer.analyze_txt(txt, chars=args.chars, out=out, log=log)
        analyzer.pretty_print(result)

    elif args.command == "pipeline":
        pdf = resolve_path(args.pdf, Path())
        txt = resolve_path(args.txt, DATA_DIR / f"{pdf.stem}.txt")
        out = resolve_path(args.out, DATA_DIR / f"{txt.stem}-结构解析结果.json")
        log.info("== 阶段1:PDF -> 文本 ==")
        text = parser.extract_pdf_text(pdf)
        txt.parent.mkdir(parents=True, exist_ok=True)
        txt.write_text(text, encoding="utf-8")
        heads = parser.detect_headings(text)
        log.info("抽取字符数:%d,疑似章节标题:%d", len(text), len(heads))
        log.info("文本已保存:%s", txt)

        log.info("== 阶段2:文本 -> DeepSeek 分析 ==")
        result = analyzer.analyze_txt(txt, chars=args.chars, out=out, log=log)
        analyzer.pretty_print(result)

    log.info("===== 任务结束 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
