---
name: hr-skill
description: This skill should be used when reviewing resumes/CVs, conducting HR interviews, screening candidates, or providing professional HR insights. It enables AI-powered HR assistant capabilities including resume parsing, candidate evaluation, interview question generation, and talent assessment.
---

# HR Skill - 智能招聘助手

## Overview

本技能包提供完整的AI驱动HR解决方案，涵盖从简历解析、候选人评估、面试安排到决策报告的全流程功能。

## 工具目录

### 一、输入层：把原始信息变成结构化数据

| 工具名称 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `load_resume_file` | 读取PDF/Word/图片简历，提取纯文本 | 文件路径或二进制流 | 原始文本 |
| `parse_resume_text` | 将简历文本转为结构化JSON | 简历文本 | 结构化简历对象 |
| `parse_job_description` | 从JD中抽取结构化要求 | JD文本 | 岗位需求JSON |
| `load_candidate_batch` | 批量加载文件夹内所有简历 | 文件夹路径 | 简历文本列表 |

### 二、分析决策层：做HR的专业判断

| 工具名称 | 功能 |
|---------|------|
| `hard_filter` | 硬性条件筛查，返回不通过原因 |
| `score_resume` | 多维度量化打分 |
| `rank_candidates` | 按总分/加权分排序 |
| `flag_risks` | 标记可疑点 |
| `detect_inconsistency` | 简历信息前后矛盾检测 |
| `compare_candidates` | 两两或一组对比 |
| `summarize_candidate` | 生成HR面试前备忘 |

### 三、输出与执行层：让决策落地

| 工具名称 | 功能 |
|---------|------|
| `generate_interview_invitation` | 生成个性化邀约邮件 |
| `generate_rejection_email` | 生成委婉拒信 |
| `push_to_ats` | 推送结构化数据到招聘系统 |
| `schedule_interview` | 自动预约面试时间 |
| `send_hr_report` | 发送决策报告给用人经理 |

### 四、知识增强层：让判断更聪明

| 工具名称 | 功能 |
|---------|------|
| `search_company_background` | 查证候选人前东家背景 |
| `skill_normalizer` | 技能别名统一 |
| `culture_fit_analyzer` | 文化契合度预判 |
| `market_salary_query` | 查询薪资范围 |

---

## 使用指南

### Step 1: 加载简历

```python
from scripts.hr_tools import load_resume_file, parse_resume_text

# 方式1: 直接读取文件
text = load_resume_file("e:/resumes/zhangsan.pdf")

# 方式2: 解析文本为结构化数据
resume = parse_resume_text(text)
```

### Step 2: 加载岗位JD

```python
from scripts.hr_tools import parse_job_description

jd = parse_job_description("""
招Python后端工程师，本科及以上，3年以上经验，
熟练掌握Django/Flask，有微服务经验优先。
""")
```

### Step 3: 硬性条件筛查

```python
from scripts.hr_tools import hard_filter

result = hard_filter(resume, jd)
# 返回: {"passed": False, "reasons": ["学历不符", "工作经验不足"]}
```

### Step 4: 打分评估

```python
from scripts.hr_tools import score_resume, flag_risks

scores = score_resume(resume, jd)
# 返回: {"total": 78, "skill_match": 85, "stability": 70, ...}

risks = flag_risks(resume)
# 返回: [{"type": "job_hopping", "severity": "high", "detail": "..."}]
```

### Step 5: 批量候选人排序

```python
from scripts.hr_tools import rank_candidates

ranked = rank_candidates([resume1, resume2, resume3], jd)
# 返回排序后的候选人列表
```

### Step 6: 生成报告

```python
from scripts.hr_tools import summarize_candidate, generate_interview_invitation

memo = summarize_candidate(resume, jd, scores, risks)

email = generate_interview_invitation(resume, jd, interview_time="2024-01-15 14:00")
```

---

## 输出格式模板

### 候选人评估报告

```
## 候选人评估报告

### 基本信息
- 姓名: [姓名]
- 学历: [学历]
- 工作年限: [X年]
- 当前职级: [职位]

### 核心技能评估
| 技能 | 熟练度 | 匹配度 |
|------|--------|--------|
| Python | 精通 | 高 |

### 经验匹配度分析
[详细分析]

### 综合评分: XX/100
- 技能匹配度: XX%
- 稳定性: XX%
- 成长性: XX%

### 优势亮点
1. [优势1]
2. [优势2]

### 风险提示
1. [风险1]
2. [风险2]

### 综合建议
[A/B/C类推荐 + 理由]

### 面试重点关注
1. [验证简历疑点]
2. [核心能力考察]
3. [动机确认]
```

---

## 功能示例

### 批量招聘流程

```python
from scripts.hr_tools import (
    load_candidate_batch, parse_job_description, 
    hard_filter, score_resume, rank_candidates,
    summarize_candidate, generate_interview_invitation
)
from scripts.ats_connector import push_to_ats_enhanced

# 1. 加载所有简历
candidates = load_candidate_batch("e:/resumes/folder")

# 2. 解析岗位JD
jd = parse_job_description(open("jd.txt").read())

# 3. 批量筛选和排序
ranked = rank_candidates([c['parsed'] for c in candidates], jd)

# 4. 获取推荐候选人(A/B类)
top_candidates = [r for r in ranked if r.get('passed', False)][:5]

# 5. 生成面试备忘并发送邀请
for candidate in top_candidates:
    resume = candidate['resume']
    scores = candidate['scores']
    
    memo = summarize_candidate(resume, jd, scores)
    invitation = generate_interview_invitation(resume, jd, "2024-01-15 14:00")
    
    # 6. 推送到ATS
    push_to_ats_enhanced(resume, jd, 'moka')
```

### 候选人对比

```python
from scripts.hr_tools import compare_candidates, score_resume

# 对比多个候选人
comparison = compare_candidates([resume1, resume2, resume3], jd)
print(comparison)
```

### 薪资查询与文化匹配

```python
from scripts.hr_tools import market_salary_query, culture_fit_analyzer, skill_normalizer

# 查询市场薪资
salary = market_salary_query("Python后端", "北京", 5)

# 分析文化契合度
culture_fit = culture_fit_analyzer(resume, ["创新", "协作", "用户导向"])

# 标准化技能名称
normalized = skill_normalizer(["js", "vue", "k8s", "ML"])
```

---

## Resources

### scripts/
| 文件 | 功能 |
|------|------|
| `hr_tools.py` | 核心HR工具集（输入、评估、输出、知识增强） |
| `resume_parser.py` | 基础简历解析器 |
| `email_generator.py` | 专业邮件模板生成器 |
| `ats_connector.py` | ATS系统连接器（支持Moka、Workday等） |

### references/
| 文件 | 内容 |
|------|------|
| `resume_analysis.md` | 简历分析专业框架、评估维度、候选人分层 |
| `interview_guide.md` | 面试评估指南、STAR法则、评分标准 |

### 依赖安装

```bash
pip install PyMuPDF python-docx pytesseract Pillow requests
```

---

## Tips for Professional HR Analysis

1. **Be Objective**: 基于简历事实评估，不做假设
2. **Quantify When Possible**: 关注量化指标
3. **Context Matters**: 考虑行业、职级、地区差异
4. **Verify Claims**: 标记需要面试验证的点
5. **Focus on Fit**: 匹配具体岗位要求
6. **Consider Growth**: 评估学习敏捷度和上升轨迹
