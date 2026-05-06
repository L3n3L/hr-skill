# HR-Skill 智能招聘助手

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/L3n3L/hr-skill?style=flat-square)](https://github.com/L3n3L/hr-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/L3n3L/hr-skill?style=flat-square)](https://github.com/L3n3L/hr-skill/network)
[![License](https://img.shields.io/github/license/L3n3L/hr-skill?style=flat-square)](https://github.com/L3n3L/hr-skill/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square)](https://www.python.org/)

</div>

> 基于 AI 的 HR 全流程招聘工具包，涵盖简历解析、候选人评估、面试安排等核心功能，开箱即用。

[English](README.md) · [文档](#使用指南) · [更新日志](CHANGELOG.md)

---

## 📖 项目简介

HR-Skill 是一款面向 HR 和招聘从业者的 AI 辅助工具，旨在将繁琐的简历筛选、候选人评估等工作自动化，让你专注于更有价值的面试和人才决策。

### 核心能力

- 🔍 **智能解析** - 支持 PDF/Word/图片简历自动解析
- 📊 **量化评估** - 多维度打分，告别主观臆断
- ⚡ **批量处理** - 一键筛选百份简历
- 📝 **自动生成** - 面试邀请、评估报告一键生成
- 🔗 **系统集成** - 对接主流 ATS 系统

---

## 🛠️ 技术栈

| 类别 | 技术 |
|:---:|:---:|
| 语言 | Python 3.8+ |
| 解析 | PyMuPDF, python-docx, pytesseract |
| ATS | Moka, Workday, 薪人薪事等 |

---

## 📁 项目结构

```
hr-skill/
├── SKILL.md                      # 技能定义文件
├── scripts/
│   ├── hr_tools.py               # 核心工具集
│   ├── resume_parser.py          # 简历解析器
│   ├── email_generator.py        # 邮件生成器
│   └── ats_connector.py         # ATS 连接器
├── references/
│   ├── resume_analysis.md        # 简历分析框架
│   └── interview_guide.md        # 面试评估指南
├── assets/                       # 资源文件
│   └── examples/                 # 示例数据
├── tests/                        # 测试用例
└── docs/                         # 详细文档
```

---

## 🚀 快速开始

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/L3n3L/hr-skill.git
cd hr-skill

# 安装依赖
pip install PyMuPDF python-docx Pillow pytesseract requests
```

### 基础用法

```python
from scripts.hr_tools import (
    parse_resume_text,      # 解析简历
    parse_job_description, # 解析 JD
    hard_filter,            # 硬性筛选
    score_resume,            # 打分评估
    flag_risks,             # 风险标记
    summarize_candidate,    # 生成面试备忘
    generate_interview_invitation  # 生成邀请邮件
)

# 1. 解析简历
resume = parse_resume_text("张三，5年经验，熟练Python...")

# 2. 解析岗位要求
jd = parse_job_description("招Python工程师，本科，3年经验...")

# 3. 硬性条件筛查
filter_result = hard_filter(resume, jd)
if not filter_result['passed']:
    print(f"不通过原因: {filter_result['reasons']}")

# 4. 打分评估
scores = score_resume(resume, jd)
print(f"综合评分: {scores['total']}/100")

# 5. 风险标记
risks = flag_risks(resume)

# 6. 生成面试备忘
memo = summarize_candidate(resume, jd, scores, risks)

# 7. 生成邀请邮件
email = generate_interview_invitation(resume, jd, "2024-01-15 14:00")
```

---

## 📋 功能列表

### 一、输入层

| 函数 | 说明 |
|:---|:---|
| `load_resume_file` | 读取 PDF/Word/图片简历 |
| `parse_resume_text` | 文本转结构化 JSON |
| `parse_job_description` | JD 解析为结构化数据 |
| `load_candidate_batch` | 批量加载文件夹内简历 |

### 二、分析决策层

| 函数 | 说明 |
|:---|:---|
| `hard_filter` | 硬性条件筛查 |
| `score_resume` | 多维度量化打分 |
| `rank_candidates` | 候选人排序 |
| `flag_risks` | 风险标记 |
| `detect_inconsistency` | 信息矛盾检测 |
| `compare_candidates` | 候选人对比 |
| `summarize_candidate` | 生成面试备忘 |

### 三、输出执行层

| 函数 | 说明 |
|:---|:---|
| `generate_interview_invitation` | 生成面试邀请 |
| `generate_rejection_email` | 生成拒信 |
| `push_to_ats` | 推送至 ATS 系统 |
| `schedule_interview` | 自动预约面试 |
| `send_hr_report` | 发送决策报告 |

### 四、知识增强层

| 函数 | 说明 |
|:---|:---|
| `search_company_background` | 查询公司背景 |
| `skill_normalizer` | 技能名称标准化 |
| `culture_fit_analyzer` | 文化契合度分析 |
| `market_salary_query` | 查询薪资范围 |

---

## 💡 使用示例

### 示例一：批量招聘流程

```python
from scripts.hr_tools import (
    load_candidate_batch,
    parse_job_description,
    rank_candidates,
    summarize_candidate,
    generate_interview_invitation
)
from scripts.ats_connector import push_to_ats_enhanced

# 1. 批量加载简历
candidates = load_candidate_batch("resumes/")

# 2. 解析 JD
jd = parse_job_description(open("jd.txt").read())

# 3. 批量排序
ranked = rank_candidates([c['parsed'] for c in candidates], jd)

# 4. 获取 Top 候选人
top_candidates = [r for r in ranked if r.get('passed')][:5]

# 5. 逐一处理
for candidate in top_candidates:
    resume = candidate['resume']
    memo = summarize_candidate(resume, jd, candidate['scores'])
    invitation = generate_interview_invitation(resume, jd, "2024-01-15 14:00")
    
    # 推送到 ATS
    push_to_ats_enhanced(resume, jd, 'moka')
    
    print(memo)
```

### 示例二：候选人对比

```python
from scripts.hr_tools import compare_candidates

# 对比多个候选人
result = compare_candidates([resume1, resume2, resume3], jd)
print(result)
```

### 示例三：薪资与文化分析

```python
from scripts.hr_tools import (
    market_salary_query,
    culture_fit_analyzer,
    skill_normalizer
)

# 查询市场薪资
salary = market_salary_query("Python后端", "北京", 5)

# 文化契合度
culture = culture_fit_analyzer(resume, ["创新", "协作", "用户导向"])

# 技能标准化
skills = skill_normalizer(["js", "vue", "k8s", "ML"])
```

---

## 📊 输出示例

### 候选人评估报告

```
## 候选人评估报告

### 基本信息
- 姓名: 张三
- 学历: 本科
- 工作年限: 5年

### 综合评分: 85/100 (A类)
| 维度 | 得分 |
|------|------|
| 技能匹配度 | 90 |
| 经验匹配度 | 85 |
| 稳定性 | 80 |
| 教育背景 | 85 |
| 成长潜力 | 80 |

### 优势亮点
1. 精通 Python + Go，技术栈与岗位高度匹配
2. 有大规模分布式系统经验

### 风险提示
1. [MEDIUM] 近期有2次短期工作经历

### 综合建议
强烈推荐面试
```

---

## 🔧 高级配置

### ATS 系统对接

```python
from scripts.ats_connector import ATSFactory

# 创建连接器
connector = ATSFactory.create('moka', api_key='your_key')

# 推送候选人
result = connector.push_candidate(candidate_data)
```

### 自定义评分权重

```python
# 自定义各维度权重
weights = {
    'skill_match': 0.40,       # 技能匹配度
    'experience_match': 0.25, # 经验匹配度
    'stability': 0.15,        # 稳定性
    'education': 0.10,        # 学历
    'growth_potential': 0.10  # 潜力
}

ranked = rank_candidates(candidates, jd, weights=weights)
```

---

## 📝 更新日志

### v1.0.0 (2024-01)
- ✨ 初始版本发布
- ✅ 支持简历解析、JD 解析
- ✅ 支持多维评估、打分排序
- ✅ 支持邮件生成、ATS 对接

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

---

## 🙏 致谢

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - PDF 处理
- [python-docx](https://github.com/python-openxml/python-docx) - Word 文档处理
- [pytesseract](https://github.com/madmaze/pytesseract) - OCR 识别

---

<div align="center">

**如果这个项目对你有帮助，请点个 ⭐ Star！**

Made with ❤️ by [Your Name](https://github.com/L3n3L)

</div>
