---
name: hr-skill
description: 智能招聘助手。读取简历文件、提供HR评估参考知识、查询薪资行情。大模型是HR的判断大脑，工具是HR的眼睛和知识库。
---

# HR Skill — 智能招聘助手

## 设计理念

```
大模型 = HR 的判断大脑（理解语义、专业评估、撰写报告、对比候选人）
MCP 工具 = HR 的眼睛和知识库（读取文件、查询行情、提供评估框架）
真人 = 最终决策者（阅读分析结果，做面试/录用决策）
```

工具不做自动解析、自动打分、自动筛选。判断交给大模型，决策交给真人。

## 工具目录（13 个）

### 数据获取

| 工具 | 说明 |
|------|------|
| `load_resume_file` | 读取 PDF/Word/图片/TXT 简历，图片型 PDF 自动 OCR（含图像预处理） |
| `load_candidate_batch` | 批量加载文件夹内所有简历 |
| `parse_jd` | 引导大模型对岗位描述进行结构化解析，提取职责/要求/薪资等 10 个关键字段 |
| `extract_resume_fields` | 从简历文本中提取 16 个结构化关键字段 |
| `clean_ocr_text` | 引导大模型对 OCR 文本进行语义级修正 |
| `generate_interview_questions` | 基于简历生成个性化面试问题（STAR+DETAIL 方法论），可结合 JD 做缺口探查 |

### 知识参考

| 工具 | 说明 |
|------|------|
| `get_evaluation_guide` | 5 维评估框架（技能/经验/稳定性/教育/潜力）、A/B/C 分层标准、STAR 面试问题模板 |
| `get_risk_checklist` | 风险信号清单（高/中/低三档），含语境豁免（应届生不适用跳槽指标等） |
| `get_skill_alias_map` | 技能别名映射表（js→JavaScript, k8s→Kubernetes, ReAct→ReAct 推理范式等） |
| `market_salary_query` | 按岗位+城市+年限查询市场薪资参考范围 |

### 辅助框架

| 工具 | 说明 |
|------|------|
| `get_match_prompt` | 简历-JD 匹配分析框架（硬性条件/技能矩阵/经验/软技能/综合匹配度） |
| `get_compare_prompt` | 候选人横向对比维度模板（基本信息/技能/经验/亮点/风险/推荐） |
| `get_report_prompt` | 给用人经理的决策报告段落框架（概览/匹配度/亮点与风险/建议） |

## 典型使用流程

### 在 Claude Code 中使用（MCP）

项目已包含 `.mcp.json`，Claude Code 打开项目时自动发现 MCP 服务器，8 个工具立即可用。

```
用户："帮我读一下 assets/简历.pdf"
→ 大模型自动调用 load_resume_file（含图像预处理 + 文本清洗）

用户："先修正一下 OCR 错误"
→ 大模型自动调用 clean_ocr_text，修正字形误识

用户："提取这份简历的关键信息"
→ 大模型自动调用 extract_resume_fields，输出结构化信息卡片

用户："解析这份 JD"
→ 大模型自动调用 parse_jd，输出结构化岗位要求

用户："把简历和 JD 做匹配分析"
→ 大模型结合 JD 解析结果和简历信息，对照评估

用户："根据评估框架给这份简历打分"
→ 大模型自动调用 get_evaluation_guide，结合简历文本分析

用户："对比这 3 位候选人"
→ 大模型自动调用 get_compare_prompt，出对比报告

用户："生成给用人经理的推荐报告"
→ 大模型自动调用 get_report_prompt，结合薪资工具给出完整建议
```

### 作为 Python 库使用

```python
from scripts.hr_tools import load_resume_file, extract_resume_fields, load_candidate_batch

# 加载单份简历
text = load_resume_file("assets/测试.pdf")

# 提取结构化字段
fields = extract_resume_fields(text)

# 解析岗位描述
jd = parse_jd("岗位描述原文...")

# 批量加载
candidates = load_candidate_batch("assets/")

# 获取参考知识
from scripts.hr_tools import (
    parse_jd,
    get_match_prompt,
    generate_interview_questions,
    get_evaluation_guide,
    get_risk_checklist,
    get_skill_alias_map,
    market_salary_query,
    get_compare_prompt,
    get_report_prompt,
)

guide = get_evaluation_guide()
risks = get_risk_checklist()
aliases = get_skill_alias_map()
salary = market_salary_query("Python开发工程师", "北京", 3)
compare = get_compare_prompt(3)
report = get_report_prompt()
questions = generate_interview_questions(text, jd_text)
```

## 评估流程建议

1. **加载** — 用 `load_resume_file` 或 `load_candidate_batch` 读取简历文本（含图像预处理）
2. **解析 JD** — 用 `parse_jd` 将岗位描述结构化，提取必备要求、加分项和职责
3. **清洗** — 用 `clean_ocr_text` 引导大模型修正 OCR 字形误识和噪声
4. **提取** — 用 `extract_resume_fields` 输出 16 字段结构化信息卡片
5. **参考** — 调用知识工具获取评估框架、风险清单、技能映射
6. **分析** — 大模型对照 JD 要求自主理解简历、套用框架、识别风险、评估匹配度
7. **面试准备** — 用 `generate_interview_questions` 生成个性化面试问题和追问链
8. **对比** — 多候选人时调用 `get_compare_prompt` 获取对比维度参考
9. **报告** — 调用 `get_report_prompt` 获取报告框架，结合薪资工具给出建议

## 注意事项

- 简历风险判断需结合语境：应届生无经验不算空窗期、学生短期项目不算频繁跳槽
- 薪资数据为税前参考，实际受公司规模、个人能力、面试表现影响
- 实习岗位有独立的薪酬体系，与正式员工不同
- OCR 识别质量受图片清晰度影响，重要简历建议索取原件
