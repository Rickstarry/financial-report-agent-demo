# 章唐茜 · 金融研报智能体(本地可运行)

2026 年北京市大学生金融人工智能竞赛 · 主攻赛道 E(研报纠错)/ G(质量评估),辅攻 B(财报分析)。

本项目是**本地可运行、可复现**的系统原型,对应决赛对“完整源代码 + 运行说明 + 样例数据可复现”的要求。核心逻辑不依赖任何 SaaS 平台;大模型通过 DeepSeek API 调用。

## 快速开始

```bash
# 1. 安装依赖(首次)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置密钥:复制 .env.example 为 .env,填入 DEEPSEEK_API_KEY

# 3. 一键跑通:PDF 财报 -> 文本 -> 报表定位 -> DeepSeek 结构化分析 -> JSON
.venv\Scripts\activate
python run.py pipeline --pdf data\美的集团-2026年半年度报告.pdf
```

样例数据已放在 `data\`:
- `美的集团-2026年半年度报告.pdf` —— 原始财报
- `美的集团-2026年半年度报告.txt` —— PDF 解析出的文本
- `美的集团-2026年半年度报告-结构解析结果.json` —— 分析结果样例

## 命令行用法

```bash
# 只做 PDF -> 文本
python run.py parse --pdf data\xxx.pdf

# 只做文本 -> DeepSeek 结构化分析
python run.py analyze --txt data\xxx.txt

# 一键完整流程(推荐)
python run.py pipeline --pdf data\xxx.pdf

# 控制模型输入量,减少 token 消耗
python run.py analyze --txt data\xxx.txt --chars 14000
```

每次运行都会在 `logs\` 生成带时间戳的日志,便于复现与排查。

## Web 界面(演示用)

```bash
.venv\Scripts\activate
streamlit run web_app.py
```

浏览器会自动打开 <http://localhost:8501>。可上传任意财报 PDF,或直接用内置美的样例一键跑完整流程;识别结果、疑似错位问题和日志都能在页面上查看。

## 目录结构与决赛要求对照

```text
.
├── run.py                 # 任务编排入口(parse / analyze / pipeline)
├── web_app.py             # Web 演示界面(Streamlit)
├── src/
│   ├── parser.py          # 数据处理:PDF -> 文本、章节粗定位
│   ├── analyzer.py        # 工具调用:报表定位 + DeepSeek API + 结果保存
│   ├── prompts/           # 提示指令(独立文件,便于调整与评审查看)
│   │   ├── analysis_system.txt
│   │   └── analysis_user.txt
│   └── logger.py          # 日志记录(控制台 + logs/ 文件)
├── data/                  # 样例数据、中间文本、输出 JSON
├── logs/                  # 每次运行的日志
├── requirements.txt       # 依赖文件
├── .env.example           # 环境变量模板(密钥不进版本库)
└── README.md              # 运行说明(本文件)
```

| 决赛要求 | 对应模块 |
| --- | --- |
| 任务编排 | `run.py`(pipeline 一键串联) |
| 工具调用 | `src/analyzer.py`(DeepSeek API) |
| 提示指令 | `src/prompts/*.txt` |
| 数据处理 | `src/parser.py` |
| 日志记录 | `src/logger.py` + `logs/` |
| 依赖与运行说明 | `requirements.txt` + 本文件 |

## 主要流程

1. `pdfplumber` 抽取 PDF 全部页面文本并标注页码;
2. 定位“合并及公司资产负债表”正文起点,按需截取片段控制 token 成本;
3. 将片段交给 DeepSeek(`deepseek-chat`),让它识别报表、期间、关键科目并标出疑似错位/乱码(赛题 E 纠错场景);
4. 结果以 JSON 落盘,全过程写入日志。

## 安全提示

- `.env` 含 API Key,**不要**提交、不要发群;
- 更换公司数据时,把财报 PDF 放入 `data\` 后运行 pipeline 即可。
