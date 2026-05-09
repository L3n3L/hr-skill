# HR Skill — 智能招聘助手

<div align="center">

[![License](https://img.shields.io/github/license/L3n3L/hr-skill?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)](https://www.python.org/)

</div>

> AI 驱动的 HR 招聘工具包。大模型是判断大脑，工具是眼睛和知识库。

---

## 设计理念

```
大模型 = HR 的判断大脑
  理解语义、专业评估、撰写报告、对比候选人

MCP 工具 = HR 的眼睛和知识库
  读取文件、查询行情、提供评估框架和风险清单

真人 = 最终决策者
  阅读分析结果，做出面试/录用/归档决策
```

工具**不做**自动解析、自动打分、自动筛选。判断交给大模型，决策交给真人。

---

## 快速开始（Claude Code 用户）

### 1. 前提条件

| 依赖 | 说明 | 必需 |
|------|------|------|
| Python 3.9+ | MCP 服务器运行环境 | 是 |
| PyMuPDF | PDF 文本提取 | 是 |
| Tesseract OCR | 图片型 PDF 的文字识别 | 仅 OCR 场景 |

### 2. 克隆并安装

```bash
git clone https://github.com/L3n3L/hr-skill.git
cd hr-skill

# Python 依赖（必须）
pip install PyMuPDF python-docx pytesseract Pillow mcp

# Tesseract OCR 引擎（可选，仅图片型 PDF 需要）
# Windows: 下载安装 https://github.com/UB-Mannheim/tesseract/releases
#          安装时勾选"中文简体"语言包
# Mac:     brew install tesseract tesseract-lang
# Linux:   sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

### 3. 在 Claude Code 中使用

项目已包含 `.mcp.json`，Claude Code 打开项目时会**自动发现并启动** MCP 服务器。

```
打开 Claude Code → 直接对话 → 8 个 HR 工具立即可用
```

无需任何额外配置。

---

## MCP 工具清单（8 个）

### 数据获取

| 工具 | 说明 | 适用场景 |
|------|------|----------|
| `load_resume_file` | 读取 PDF/Word/图片/TXT 简历，图片型 PDF 自动 OCR | 单份简历加载 |
| `load_candidate_batch` | 批量加载文件夹内所有简历 | 批量筛选 |

### 知识参考

| 工具 | 说明 |
|------|------|
| `get_evaluation_guide` | 5 维评估框架、A/B/C 分层标准、STAR 面试问题模板 |
| `get_risk_checklist` | 风险信号清单（高/中/低三档），含语境豁免说明 |
| `get_skill_alias_map` | 技能别名映射（js→JavaScript, k8s→Kubernetes 等） |
| `market_salary_query` | 按岗位+城市+年限查询市场薪资参考范围 |

### 辅助框架

| 工具 | 说明 |
|------|------|
| `get_compare_prompt` | 候选人横向对比维度模板 |
| `get_report_prompt` | 给用人经理的决策报告段落框架 |

---

## 典型使用流程

```
1. 加载简历
   你说："帮我读一下 assets/测试.pdf"

2. 大模型评估
   你说："根据评估框架，给这份简历打分"

3. 横向对比
   你说："用对比框架，比较这 3 位候选人"

4. 生成报告
   你说："生成给用人经理的推荐报告"
```

大模型会自动调用对应工具获取参考框架，结合简历文本完成分析。

---

## 环境配置详解

### Python 依赖

```bash
pip install PyMuPDF python-docx pytesseract Pillow mcp
```

| 包名 | 用途 |
|------|------|
| `PyMuPDF` | PDF 文本提取与 OCR 图片渲染 |
| `python-docx` | Word 文档读取 |
| `pytesseract` | OCR 引擎 Python 封装 |
| `Pillow` | 图片处理与 OCR 图片预处理 |
| `mcp` | MCP 协议服务端框架 |

### Tesseract OCR 安装（可选）

> 如果你的简历都是文字型 PDF 或 Word/TXT，**不需要安装 Tesseract**。
> 只有遇到纯图片型 PDF 时才需要。

**Windows：**

1. 下载安装包：[UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/releases)
2. 运行安装程序，在语言选择步骤勾选 **"中文简体"（Chinese Simplified）**
3. 默认安装到 `C:\Program Files\Tesseract-OCR\`，服务器会自动探测该路径
4. 如果安装到自定义路径，确保路径在代码的自动探测列表中（支持 C/D/E 盘）

**Mac：**

```bash
brew install tesseract tesseract-lang
```

**Linux：**

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

### 验证安装

```bash
# 验证 Python 依赖
python -c "import fitz; import pytesseract; from docx import Document; print('OK')"

# 验证 Tesseract（命令行）
tesseract --version

# 验证完整 OCR 流程
python -c "
from scripts.hr_tools import load_resume_file
text = load_resume_file('assets/测试.pdf')
print(f'识别 {len(text)} 字符，OK')
"
```

---

## 常见问题

### Q: Claude Code 中工具调用报 "AbortError"？

A: 通常是因为首次调用时冷导入大型库超时。重启 MCP 服务器即可（`Ctrl+Shift+P` → `Reload Window`）。项目已做启动预热，正常情况不会出现。

### Q: PDF 识别出来是乱码？

A: 检查 Tesseract 是否安装、中文简体语言包是否勾选。运行 `tesseract --list-langs` 应该能看到 `chi_sim`。

### Q: OCR 识别准确度低？

A: OCR 对图片质量敏感，确保简历清晰。如果是扫描件，建议用 300dpi 以上扫描。

### Q: 不想装 Tesseract 能用吗？

A: 如果简历是文字型 PDF、Word 或 TXT，完全不需要 Tesseract。只有纯图片型 PDF 才触发 OCR。

---

## 项目结构

```
hr-skill/
├── .mcp.json                  # Claude Code MCP 自动发现配置
├── mcp_server.py              # MCP 服务入口
├── CLAUDE.md                  # 项目语言规范
├── SKILL.md                   # Skill 入口定义
├── scripts/
│   ├── hr_tools.py            # 核心工具集（8 个工具）
│   └── __init__.py
├── references/
│   ├── resume_analysis.md     # 简历分析参考框架
│   └── interview_guide.md     # 面试评估指南
├── assets/                    # 示例简历
└── README.md
```

---

## 贡献

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/xxx`)
3. 提交更改
4. 推送并创建 Pull Request

---

## 许可证

[MIT License](LICENSE)

---

## 致谢

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF 处理
- [pytesseract](https://github.com/madmaze/pytesseract) — OCR 识别
- [python-docx](https://github.com/python-openxml/python-docx) — Word 文档处理

---

<div align="center">

**如果这个项目对你有帮助，请点个 ⭐ Star！**

</div>
