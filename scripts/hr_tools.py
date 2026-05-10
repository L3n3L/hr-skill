"""
HR 智能招聘工具集（精简版）

角色分离：
- 大模型 = HR 的判断大脑（理解语义、专业评估、撰写报告、对比候选人）
- 工具 = HR 的眼睛和知识库（读取文件、查询行情、提供评估框架）

本模块只提供数据获取和知识参考两类工具，
不做任何自动解析、自动打分、自动筛选。
"""

import re
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


# ==================== 一、数据获取层 ====================

def load_resume_file(file_path: str) -> str:
    """
    读取简历文件（PDF/Word/图片/TXT），返回纯文本供大模型理解

    支持格式：.pdf / .docx / .txt / .jpg / .png
    图片型 PDF 自动通过 OCR 提取文字
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    text = ""

    try:
        if suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        elif suffix == '.pdf':
            try:
                import fitz
                doc = fitz.open(file_path)
                for page in doc:
                    page_text = page.get_text().strip()
                    if page_text:
                        text += page_text + '\n'
                    else:
                        ocr_text = _ocr_pdf_page(page)
                        if ocr_text:
                            text += ocr_text + '\n'
                doc.close()
            except ImportError:
                return "[需要安装 PyMuPDF: pip install PyMuPDF]"

        elif suffix == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text = '\n'.join([p.text for p in doc.paragraphs])
            except ImportError:
                return "[需要安装 python-docx: pip install python-docx]"

        elif suffix in ['.jpg', '.jpeg', '.png']:
            try:
                import pytesseract
                from PIL import Image
                _auto_detect_tesseract()
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            except ImportError:
                return "[需要安装 pytesseract 和 PIL: pip install pytesseract Pillow]"
            except Exception as e:
                return f"[图片 OCR 失败: {e}]"

    except Exception as e:
        return f"[读取文件失败: {e}]"

    # 对 OCR 输出做基础清洗
    if suffix != '.txt':
        text = _normalize_ocr_text(text)

    return text


def load_candidate_batch(folder_path: str,
                         extensions: List[str] = None,
                         max_workers: int = 4) -> List[Dict]:
    """
    批量加载文件夹内所有简历（多线程并行处理，图片型 PDF 密集场景可大幅加速）

    Args:
        folder_path: 文件夹路径
        extensions: 支持的文件扩展名，默认 ['.txt', '.pdf', '.docx', '.jpg', '.png']
        max_workers: 并行线程数，默认 4（OCR 密集时可调高至 6-8）

    Returns:
        [{'filename': str, 'text': str, 'error': str|None}]，按文件名排序
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if extensions is None:
        extensions = ['.txt', '.pdf', '.docx', '.jpg', '.png']

    folder = Path(folder_path)

    # 先收集所有文件
    files = []
    for ext in extensions:
        files.extend(folder.glob(f"*{ext}"))

    if not files:
        return []

    # 多线程并行加载
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(load_resume_file, str(f)): f for f in files}
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                text = future.result()
                results.append({
                    'filename': file_path.name,
                    'text': text,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'filename': file_path.name,
                    'text': '',
                    'error': str(e)
                })

    # 按文件名排序，保证输出顺序稳定
    results.sort(key=lambda x: x['filename'])
    return results


# ==================== 二、知识参考层 ====================

def get_evaluation_guide() -> str:
    """
    返回 HR 评估框架，供大模型参考后自主评估

    包含：评估维度与权重、候选人分层标准（A/B/C）、STAR 面试问题模板
    """
    return """## HR 简历评估参考框架

### 评估维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 技能匹配度 | 30% | 与岗位所需技能的匹配程度，包括编程语言、框架、工具、专业领域知识 |
| 经验匹配度 | 25% | 项目经验的复杂度、规模、角色，是否与目标岗位相关 |
| 稳定性 | 20% | 工作/项目时间跨度是否合理，适合岗位级别的稳定预期（注意：对实习生/应届生不适用跳槽指标） |
| 教育背景 | 15% | 学历层次、专业相关性、学校水平 |
| 成长潜力 | 10% | 学习能力、技术深度轨迹、自驱力、获奖和竞赛经历 |

### 候选人分层

- **A 类（强烈推荐）**：技能高度匹配，有亮点项目或稀缺技能，发展轨迹清晰
- **B 类（备选）**：基本满足要求，无明显短板但缺少突出亮点
- **C 类（不推荐）**：核心要求不满足，或存在硬伤（学历不符、技能缺口大）

### 面试重点关注方向

- 背景核实：具体角色和贡献、主要业绩、离职/换岗原因
- 能力验证：最擅长的技术领域、最大技术挑战及解决方案
- 动机匹配：对岗位的兴趣、职业发展规划

### STAR 面试问题模板

1. 请用 STAR 法则描述一个你主导的最成功的项目或任务
2. 描述一次你解决复杂技术问题的经历，你当时怎么分析的？
3. 如果给你一个新项目/新任务，你会如何规划和开始？
4. 讲一次你在团队中遇到分歧的情况，你如何处理的？
5. 你最近学到的最有价值的技能或知识是什么？怎么学的？

### 使用说明

以上为参考框架。请根据候选人实际简历内容和岗位要求，
运用你的专业判断给出个性化的评估和建议，切勿机械套用。"""


def get_risk_checklist() -> str:
    """
    返回简历风险信号清单，供大模型自主判断

    注意：此为参考清单，不是自动检测规则。
    是否构成风险取决于具体语境和岗位级别。
    """
    return """## 简历风险信号参考清单

### 高优先级关注

- **频繁更换**：工作时间过短（<6个月）或多次短周期变动，需了解每次的真实原因
- **时间线矛盾**：教育经历时间与工作经历时间存在重叠或矛盾
- **空窗期**：工作或学习之间存在较长空白期（>6个月），需了解原因
- **职位/职级下降**：职业轨迹呈现下行趋势

### 中优先级关注

- **描述空洞**：工作/项目描述缺少具体量化数据，全篇"参与了/负责了"无成果
- **技能与实际不匹配**：列出大量技能但项目描述中未见实际应用
- **行业跳变**：跨行业跳转缺乏合理逻辑

### 低优先级关注

- **信息缺失**：缺少期望薪资、到岗时间等基础信息
- **格式问题**：排版混乱、错别字较多（排除 OCR 噪声）

### 语境豁免

以下情况不应判定为风险：
- 应届生/实习生无工作经验 → 不算空窗期
- 学生期间的短期项目/实习 → 不算频繁跳槽
- 在校项目时间集中 → 可能是课程大作业或竞赛期

### 使用说明

请结合候选人背景（应届/在职、岗位级别）和具体语境，
运用专业判断逐条审视。标记为"需面试验证"比"直接否决"更合理。"""


def get_skill_alias_map() -> Dict[str, Dict[str, str]]:
    """
    返回技能别名映射表，供大模型查询参考

    大模型应自行理解技能间的等同关系，
    此表仅作为常见别名的快速查询补充。
    """
    return {
        # 编程语言
        'js': {'standard': 'JavaScript', 'category': '前端'},
        'ts': {'standard': 'TypeScript', 'category': '前端'},
        'py': {'standard': 'Python', 'category': '后端'},
        'go': {'standard': 'Go', 'category': '后端'},
        'rb': {'standard': 'Ruby', 'category': '后端'},
        'cpp': {'standard': 'C++', 'category': '后端'},
        'cs': {'standard': 'C#', 'category': '后端'},
        # 前端
        'vue': {'standard': 'Vue.js', 'category': '前端'},
        'ng': {'standard': 'Angular', 'category': '前端'},
        # 数据库
        'pg': {'standard': 'PostgreSQL', 'category': '数据库'},
        'mongo': {'standard': 'MongoDB', 'category': '数据库'},
        'es': {'standard': 'Elasticsearch', 'category': '搜索'},
        # DevOps
        'k8s': {'standard': 'Kubernetes', 'category': 'DevOps'},
        'gcp': {'standard': 'Google Cloud Platform', 'category': '云平台'},
        'az': {'standard': 'Azure', 'category': '云平台'},
        # AI / ML
        'ml': {'standard': '机器学习', 'category': 'AI'},
        'tf': {'standard': 'TensorFlow', 'category': 'AI'},
        'torch': {'standard': 'PyTorch', 'category': 'AI'},
        'dl': {'standard': '深度学习', 'category': 'AI'},
        'nlp': {'standard': '自然语言处理', 'category': 'AI'},
        'cv': {'standard': '计算机视觉', 'category': 'AI'},
        # 重点：注意大小写敏感的别名
        'ReAct': {'standard': 'ReAct 推理范式', 'category': 'AI'},
        'react': {'standard': 'React', 'category': '前端'},
    }


def market_salary_query(position: str, city: str, experience_years: int = 0) -> str:
    """
    查询指定岗位在指定城市的市场薪资参考范围

    返回可读的文本供大模型参考，不做自动判断。

    Args:
        position: 岗位名称
        city: 城市名称
        experience_years: 工作年限（可选，用于调整薪资区间）
    """
    # 基础薪资表（月薪，单位 K）
    base_salary = {
        'python': (15, 25, 45),
        'java': (12, 20, 40),
        '前端': (12, 20, 38),
        '算法': (20, 35, 60),
        '产品经理': (10, 18, 35),
        '运营': (8, 14, 28),
        '实习': (3, 6, 12),
        '实习生': (3, 6, 12),
    }

    # 城市系数
    city_factor = {
        '北京': 1.3, '上海': 1.25, '深圳': 1.2, '杭州': 1.15,
        '广州': 1.0, '成都': 0.9, '武汉': 0.85, '西安': 0.8,
    }

    # 经验系数
    if experience_years <= 0:
        exp_factor = 0.6
    elif experience_years <= 2:
        exp_factor = 0.7
    elif experience_years <= 5:
        exp_factor = 1.0
    elif experience_years <= 10:
        exp_factor = 1.3
    else:
        exp_factor = 1.5

    # 匹配岗位
    pos_key = 'python'
    pos_lower = position.lower()
    if '实习' in pos_lower:
        pos_key = '实习生'
    else:
        for key in ['算法', '前端', '运营', 'java', 'python', '产品经理']:
            if key in pos_lower:
                pos_key = key
                break

    low, mid, high = base_salary.get(pos_key, base_salary['python'])
    factor = city_factor.get(city, 0.9)

    monthly = (
        int(low * factor * exp_factor),
        int(mid * factor * exp_factor),
        int(high * factor * exp_factor)
    )
    annual = tuple(m * 12 for m in monthly)

    result = f"""## {position}（{city}）市场薪资参考

- 工作年限: {experience_years}年
- 月薪范围: {monthly[0]}K - {monthly[1]}K - {monthly[2]}K（低-中-高）
- 年薪范围: {annual[0]}K - {annual[1]}K - {annual[2]}K

注意：以上为税前参考范围，实际薪资受公司规模、个人能力、
面试表现等多因素影响。实习岗位通常有单独的实习生薪酬体系。"""
    return result


# ==================== 三、辅助框架层 ====================

def get_compare_prompt(candidate_count: int = 2) -> str:
    """
    返回候选人横向对比框架，供大模型参考后生成对比报告
    """
    return f"""## 候选人横向对比框架

请从以下维度对 {candidate_count} 位候选人进行对比分析：

| 维度 | 说明 |
|------|------|
| 基本信息 | 学历、工作年限、目标岗位匹配度 |
| 核心技能 | 与岗位要求的技能矩阵对比 |
| 项目经验 | 项目复杂度、角色、产出质量 |
| 优势亮点 | 每位候选人独特的竞争力 |
| 风险提示 | 需关注或面试验证的点 |
| 综合推荐 | 给出排名和推荐理由 |

### 输出格式建议

1. 先给出对比总表
2. 再展开每位候选人的详细分析
3. 最后给出综合推荐排序

### 使用说明

请基于简历原始文本做出你的独立判断，以上维度仅供参考。
不要机械填表——如果某维度不适用或对比意义不大，可以简化或跳过。"""


def get_report_prompt() -> str:
    """
    返回决策报告框架，供大模型参考后生成给用人经理的报告
    """
    return """## HR 决策报告框架

以下为给用人经理的推荐报告参考结构：

### 1. 候选人概览
- 基本信息（姓名、学历、工作年限）
- 核心技能摘要
- 综合评分定位（A/B/C 类 + 简短理由）

### 2. 匹配度分析
- 技能与岗位要求的对照
- 项目经验与岗位职责的相关性
- 成长潜力评估

### 3. 亮点与风险
- 突出优势（为什么推荐）
- 需关注的点（面试时重点验证）

### 4. 建议
- 推荐面试流程（几轮、侧重点）
- 建议面试官重点关注方向
- 薪资建议参考

### 使用说明

请根据候选人的实际简历内容填充上述框架。
每条建议都应基于简历中的具体事实，而非泛泛而谈。
如果候选人是应届生/实习生，调整评估标准，更关注成长潜力而非经验年限。"""


def get_match_prompt() -> str:
    """
    返回简历-JD 匹配分析框架，引导大模型对照岗位要求评估候选人匹配度

    工具只提供匹配维度和输出结构，实际匹配判断由大模型完成。
    使用前请确保已通过 parse_jd 和 extract_resume_fields 获取了结构化数据。
    """
    return """## 简历-JD 匹配分析框架

请将候选人的简历与岗位描述进行逐项对照分析，输出匹配度评估。

### 一、硬性条件检查

首先检查候选人是否满足岗位的硬性门槛：

| 条件项 | JD 要求 | 候选人情况 | 判定 |
|--------|---------|------------|:--:|
| 学历 | ... | ... | 满足/不满足/接近 |
| 工作年限 | ... | ... | 满足/不满足/接近 |
| 专业方向 | ... | ... | 满足/不满足/接近 |
| 工作地点 | ... | ... | 匹配/不匹配/可协商 |
| 其他硬性要求 | ... | ... | 满足/不满足/接近 |

判定规则：
- "满足"=明确达标；"不满足"=明确不达标需标记为硬伤；"接近"=处于边界可面试验证
- 任一硬性条件不满足，需在综合评估中明确标注风险等级

### 二、技能覆盖矩阵

| JD 要求技能 | 重要程度 | 候选人具备程度 | 覆盖判定 | 面试验证方向 |
|-------------|:--------:|:-------------:|:--------:|-------------|
| 技能A | 必备 | 精通/熟练/了解/缺失 | 完全/部分/未覆盖 | 如何验证 |
| 技能B | 加分 | 精通/熟练/了解/缺失 | 完全/部分/未覆盖 | 如何验证 |
| ... | ... | ... | ... | ... |

重要程度分"必备"和"加分"两档，从 JD 解析结果中获取。

### 三、经验匹配度

| 维度 | JD 期望 | 候选人经验 | 匹配度 |
|------|---------|-----------|:--:|
| 行业背景 | ... | ... | 高/中/低 |
| 项目类型 | ... | ... | 高/中/低 |
| 项目规模 | ... | ... | 高/中/低 |
| 担任角色 | ... | ... | 高/中/低 |
| 技术深度 | ... | ... | 高/中/低 |

### 四、软技能对照

| 软技能维度 | JD 期望 | 候选人表现 | 评估 |
|-----------|---------|-----------|:--:|
| 沟通协作 | ... | ... | 匹配/待验证/存疑 |
| 自驱力 | ... | ... | 匹配/待验证/存疑 |
| 学习能力 | ... | ... | 匹配/待验证/存疑 |
| 领导力 | ... | ... | 匹配/待验证/存疑 |

### 五、综合匹配度

```
综合匹配度: XX%（加权计算）
匹配等级: 高度匹配 / 基本匹配 / 勉强匹配 / 不推荐

**优势**
- ...
- ...

**差距**
- ...
- ...

**关键风险**
- ...（标注是否为硬伤）
```

加权建议：技能覆盖 35%、经验匹配 30%、硬性条件 20%、软技能 15%。应届生调整权重：技能覆盖 25%、经验匹配 15%、硬性条件 15%、软技能 10%、成长潜力 35%。

### 六、面试验证建议

针对匹配分析中暴露的差距和疑点，给出具体的面试探查方向：

1. **技术验证方向** — 针对技能缺口或简历中模糊的技能描述
2. **经验深挖方向** — 针对简历中描述不够具体的项目经验
3. **动机探查方向** — 针对行业/岗位切换的动机和期望
4. **稳定性评估方向** — 针对工作经历中的风险信号

### 使用说明

请基于已有的 JD 解析结果和简历提取信息进行对照分析。
每条判定都应基于具体证据（JD 原文和简历原文），不要主观臆断。
不要机械计算分数——如果某维度信息不足，标注"待面试验证"比强行打分更合理。"""


def generate_interview_questions(resume_text: str, jd_text: str = "") -> str:
    """
    基于简历和岗位描述生成个性化面试问题

    自动识别简历中的项目亮点、技能声明、经历疑点和与 JD 的差距，
    引导大模型生成针对性的面试问题，而非通用模板。

    工具只提供问题生成框架和设计原则，实际问题由大模型生成。
    """
    jd_section = ""
    if jd_text:
        jd_section = f"""
### 岗位描述（JD）

{jd_text}
"""

    return f"""## 个性化面试问题生成

请基于以下简历内容，为面试官生成一套个性化的面试问题。目的是帮助面试官高效验证候选人的真实能力，而非机械走流程。

### 设计原则

1. **基于具体事实提问** — 每个问题必须指向简历中的具体项目、技能或经历，不要问泛泛的"你最大的优点是什么"
2. **用 STAR+DETAIL 方法论深挖** — 追问情境(Situation)、任务(Task)、行动(Action)、结果(Result)，并在 Action 环节追问方向依据(Direction)、执行步骤(Execution)、遇到的困难(Trouble)、调整过程(Adjustment)、反思总结(Insight)
3. **交叉验证** — 对同一能力从不同侧面提问（如项目细节 + 技术原理 + 决策依据），防止背诵式回答
4. **尖锐但公正** — 对简历中的疑点（空窗期、频繁变动、技能与经验不匹配）直接提问，但保持中立语气
5. **控制数量** — 每类 2-3 个核心问题 + 追问方向，总数控制在 10-15 个核心问题，确保 45-60 分钟内可完成

### 问题生成框架

请按以下五类生成问题，每类标注设计意图。

---

#### 第一类：项目深挖（3-4 个核心问题）

从简历中选择 1-2 个最有代表性的项目，用 STAR+DETAIL 方法设计追问链。

对每个选定项目，生成：
- **开场问题** — 让候选人用自己的话描述项目
- **Action 追问** — 深入追问个人角色、技术选型依据、实现细节
- **Trouble 追问** — 追问项目中的最大挑战、失败经历、如何应对
- **Insight 追问** — 追问复盘反思，"如果重来会怎么做"

输出格式：
```
**项目深挖：XXX 项目**

| 追问层级 | 问题 | 设计意图 |
|----------|------|----------|
| 开场 | ... | 获取候选人视角下的项目全貌 |
| Action | ... | 验证个人实际贡献和技术决策能力 |
| Trouble | ... | 评估问题解决能力和抗压性 |
| Insight | ... | 考察复盘习惯和成长潜力 |

**追问技巧**：观察候选人是否能给出"只有真正做过才知道"的细节——
技术选型的权衡过程、踩过的坑、和同事的分歧等。
```

---

#### 第二类：技能验证（2-3 个核心问题）

针对简历中声明的核心技术技能，设计验证性问题。

- 对每个关键技能，问"怎么用的"而非"会不会"
- 追问深度超过简历描述的边界，探测真实水平
- 关注技能的横向广度（相关技术生态）和纵向深度（底层原理）

输出格式：
```
**技能验证：XXX 技能**

| 问题 | 设计意图 | 好回答的特征 |
|------|----------|-------------|
| ... | 验证实际应用深度 | 能描述具体场景、数据量级、异常处理 |
| ... | 验证底层理解 | 能讲清原理、对比替代方案 |
| ... | 验证学习方式 | 能描述学习路径和知识体系构建过程 |
```

---

#### 第三类：经历疑点探查（2-3 个核心问题）

根据简历风险信号（参考 get_risk_checklist），生成针对性的探查问题。

常见疑点类型：
- **空窗期** — 直接询问原因和期间做了什么
- **频繁变动** — 了解每次变动的原因和决策逻辑
- **职位/职级下行** — 了解职业选择背后的考量
- **技能与经验不匹配** — 探查看似矛盾的技能声明的真实性
- **描述空洞** — 追问具体的量化成果

输出格式：
```
**疑点探查**

| 疑点 | 简历依据 | 提问方式 | 设计意图 |
|------|----------|----------|----------|
| 空窗期 | 2024.03-2024.09 无记录 | "这段时间你在做什么？" | 了解真实原因，观察反应是否自然 |
| ... | ... | ... | ... |

**提问技巧**：用开放而非审问的语气——"能聊聊这段时间吗？"
比"你为什么有半年没工作？"更合适。
```

---

#### 第四类：缺口探查（2-3 个核心问题，有 JD 时才生成）

如果提供了岗位描述，识别简历与 JD 之间的能力差距，设计探查问题。

- 区分"可培养的缺口"和"硬伤"，前者设计验证潜力的问题，后者直接确认
- 对简历未提及但 JD 强调的技能，问"是否有接触过类似领域"

输出格式：
```
**缺口探查**

| JD 要求 | 简历现状 | 探查问题 | 验证目标 |
|----------|----------|----------|----------|
| 要求 Kafka 经验 | 简历未提及消息队列 | "是否有消息队列相关的项目或学习经验？" | 区分"没写"和"没有" |
| ... | ... | ... | ... |
```

---

#### 第五类：动机与期望（2-3 个核心问题）

评估候选人的求职动机、职业规划和与团队的契合度。

输出格式：
```
**动机与期望**

| 问题 | 设计意图 | 红旗信号 |
|------|----------|----------|
| "为什么想离开当前/上一家公司？" | 了解真实离职原因 | 一味抱怨前东家、原因模糊不清 |
| "未来 2-3 年的职业规划是什么？" | 评估目标是否与岗位成长路径匹配 | 规划与本岗位无关、回答空洞 |
| "对薪资和工作方式的期望？" | 确认双方预期是否在可协商范围内 | 期望远超岗位预算、对工作方式无弹性 |
```

---

### 全局输出要求

1. 在每类问题之前，先用 1-2 句话说明为什么选择这些方向（基于简历的什么具体信息）
2. 问题本身用直接引语格式（面试官可以直接念出来的自然口语）
3. 追问部分可以是问题清单，因为面试官需要灵活选择
4. 最后给出一个"建议面试结构"——几轮面试、每轮侧重点、建议时长

### 简历原文

{resume_text}
{jd_section}"""


def parse_jd(jd_text: str) -> str:
    """
    返回 JD 结构化解析框架，引导大模型从岗位描述中提取关键要求

    覆盖岗位基础信息、核心职责、任职要求、薪资与业务背景等维度。
    工具只提供提取框架和输出规范，实际解析判断由大模型完成。
    """
    return f"""## JD 岗位描述结构化解析

请从以下岗位描述中提取关键信息，按指定格式输出。这份解析结果将用于后续的简历匹配和面试问题生成。

### 提取字段（10 个）

**基础信息**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 岗位名称 | 职位全称 | JD 标题或首段 |
| 所属部门 | 部门/事业部 | 从组织架构描述推断 |
| 汇报对象 | 汇报层级 | 从"汇报给""向XX汇报"提取 |
| 工作地点 | 城市+办公方式 | 是否标注远程/混合/现场 |

**岗位职责**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 核心职责 | 3-5 条主要工作内容 | 从"岗位职责""工作内容"段落提炼 |

**任职要求**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 必备要求 | 学历/年限/技能的硬性门槛 | 从"任职资格"提取必需条件 |
| 加分要求 | 锦上添花但非必须的条件 | 从"优先""加分项"提取 |
| 软技能期望 | 沟通/协作/自驱力等能力 | 从行为描述推断 |

**其他信息**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 薪资范围 | JD 中明确的薪资区间 | 直接提取，无则标注"未提及" |
| 业务背景 | 团队/业务线简介 | 从公司或业务描述提取 |

### 提取规则

1. 只提取 JD 中明确写出的信息，缺失字段标注"未提及"
2. 核心职责用简洁的动宾结构概括（如"负责千万级用户产品的后端架构设计"）
3. 必备要求和加分要求严格区分，不要混在一起
4. 技能要求归纳为技能关键词（如 Python、Kubernetes、数据分析），而非复制长句
5. 如果 JD 描述模糊（如"熟悉主流微服务框架"），保留原表述并在备注标注"需用人经理确认"

### 输出格式

```
## JD 信息卡片

**基础信息**
| 字段 | 内容 |
|------|------|
| 岗位名称 | ... |
| 所属部门 | ... |
| 汇报对象 | ... |
| 工作地点 | ... |

**岗位职责**
1. ...
2. ...
3. ...

**任职要求**
| 类别 | 内容 |
|------|------|
| 学历要求 | ... |
| 工作年限 | ... |
| 必备技能 | 技能A、技能B、技能C |
| 加分技能 | 技能D、技能E（非必须） |
| 软技能期望 | ... |

**其他信息**
| 字段 | 内容 |
|------|------|
| 薪资范围 | ... |
| 业务背景 | ... |

**筛选关键词**（用于简历初筛快速匹配）
- 技能关键词: ...
- 经验关键词: ...
- 硬性门槛: ...
```

### JD 原文

{jd_text}"""


def extract_resume_fields(resume_text: str) -> str:
    """
    返回简历关键字段结构化提取框架，引导大模型从简历文本中提取关键信息

    工具只提供提取框架和输出规范，实际提取判断由大模型完成。
    """
    return f"""## 简历关键字段提取

请从以下简历文本中提取关键信息，按指定格式输出。

### 提取字段（16 个）

**基础信息**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 姓名 | 候选人全名 | 通常在简历开头或顶部 |
| 性别 | 男/女 | 从身份证号、照片或称呼推断 |
| 年龄 | 具体年龄或出生年份 | 从出生日期或教育经历推算 |
| 求职状态 | 在职/离职/应届/实习 | 从工作经历时间线判断 |
| 工作年限 | X年 | 从工作经历累计计算 |
| 最高学历 | 学历+学校+专业 | 取最高学历条目 |
| 现居地址 | 城市 | 从联系地址或期望城市推断 |

**求职期望**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 期望岗位 | 意向职位 | 从求职意向栏提取 |
| 期望行业 | 意向行业 | 从求职意向或经历推断 |
| 期望薪资 | 金额 | 从求职意向栏提取 |
| 期望城市 | 城市 | 从求职意向栏提取 |

**经历**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 教育经历 | 学校+专业+学历+时间段 | 按时间倒序列出 |
| 工作经历 | 公司+岗位+时间段+职责 | 按时间倒序列出，实习单独标注 |
| 项目经历 | 项目名+时间段+技术栈+描述 | 按时间倒序列出 |

**能力与补充**

| 字段 | 说明 | 提取方式 |
|------|------|----------|
| 技能清单 | 技能+熟练度（精通/熟练/了解） | 从专业技能栏和项目技术栈汇总 |
| 获奖与证书 | 竞赛/奖学金/认证 | 逐条列出，含级别和年份 |
| 语言能力 | 语种+等级/分数 | CET-4/6、雅思、托福等 |
| 社交链接 | GitHub/博客/LinkedIn | 从联系栏或个人介绍提取 |
| 自我评价 | 原文摘要或关键词 | 从自我评价栏提取，保持原意 |

### 提取规则

1. **只提取简历中明确写出的信息**，缺失的字段标注"未提及"，不要编造或猜测
2. 工作年限按实际工作月份累加，实习不计入；应届生标"应届"
3. 同一字段如有多条（如多段工作经历），逐条列出
4. OCR 噪声导致的拼写错误，根据上下文合理修正，修正处用「」标注原始 OCR 文字
5. 日期格式统一为 YYYY.MM
6. 技能熟练度根据描述词判断：精通/熟练掌握 → 精通，熟悉/掌握 → 熟练，了解/接触 → 了解

### 输出格式

```
## 候选人信息卡片

**基本信息**
| 字段 | 内容 |
|------|------|
| 姓名 | ... |
| 性别 | ... |
| 年龄 | ... |
| 求职状态 | ... |
| 工作年限 | ... |
| 最高学历 | ... |
| 现居地址 | ... |

**求职期望**
| 期望岗位 | 期望行业 | 期望薪资 | 期望城市 |
|----------|----------|----------|----------|
| ... | ... | ... | ... |

**教育经历**
| 时间 | 学校 | 专业 | 学历 |
|------|------|------|------|
| ... | ... | ... | ... |

**工作经历**
| 时间 | 公司 | 岗位 | 主要职责 |
|------|------|------|----------|
| ... | ... | ... | ... |

**项目经历**
| 时间 | 项目名 | 技术栈 | 项目描述 |
|------|--------|--------|----------|
| ... | ... | ... | ... |

**技能清单**
| 技能 | 熟练度 |
|------|--------|
| ... | 精通/熟练/了解 |

**获奖与证书**
| 时间 | 名称 | 级别 |
|------|------|------|
| ... | ... | ... |

**语言能力**
| 语种 | 等级/分数 |
|------|-----------|
| ... | ... |

**社交链接**
| 平台 | 链接 |
|------|------|
| ... | ... |

**自我评价**
...（保留原文关键表述，不超过 100 字）
```

### 简历原文

{resume_text}"""


def clean_ocr_text(ocr_text: str) -> str:
    """
    引导大模型对 OCR 文本进行语义级修正

    正则能去乱码，但修不了"桌架→框架"这类语义错误。这个工具引导大模型
    利用上下文理解，将 OCR 错误修正为正确的专业术语和自然语言。

    工具只返回修正提示框架，不自动修改——判断权在大模型。
    """
    template = """## OCR 文本语义修正

以下简历文本来自 OCR 识别，可能包含识别错误。请用你的语义理解能力修正，
保持原始信息不增不减。

### 常见 OCR 错误类型及修正示例

| 错误类型 | OCR 原文 | 修正后 |
|----------|----------|--------|
| 字形误识 | 桌架、粲通、莲端 | 框架、精通、前端 |
| 拆分合并 | 计 算 机 / Chromey8 | 计算机 / Chrome V8 |
| 中英混杂 | 至至今、fF | (删除噪声符号) |
| 专有名词 | LangChain→LangChain | 保持原名不修正 |
| 联系人信息 | itps://xxx / hitps://xxx | https://xxx |
| 上下文推断 | "985 211" + 学校名 | 确认为学校标签 |

### 修正规则

1. **仅修正明显的 OCR 错误**，不确定的地方保留原文
2. 专业技术名词（Vue.js、PyTorch、Kubernetes）即使 OCR 有错也修正
3. 人名、公司名如不确认正确写法则保留 OCR 原文
4. 不要增删简历实质内容（不补充缺失信息，不删除存在的条目）
5. 修正处无需标注

### 输出格式

先输出修正后的完整文本，再简要列出主要修正项：

```
## 修正后文本
（完整简历文本）

## 主要修正
| 位置 | 原文 | 修正 |
|------|------|------|
| 第X段 | 桌架 | 框架 |
| 第X段 | itps:// | https:// |
...
```

### 原始 OCR 文本

%s""" % ocr_text
    return template


# ==================== 内部辅助函数 ====================

def _ocr_pdf_page(page) -> str:
    """对 PDF 页面进行 OCR 识别"""
    try:
        import fitz as _fitz
        import pytesseract
        from PIL import Image
        import io

        _auto_detect_tesseract()

        # 渲染页面为图片（2 倍缩放，保证文字清晰度）
        mat = _fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        # 图像预处理：灰度 + 对比度增强（不做二值化，保留 LSTM 所需灰度信息）
        image = _preprocess_image(image)

        # psm 4: 假设单列变大小文本，适合简历布局
        config = '--psm 4'
        try:
            return pytesseract.image_to_string(image, lang='chi_sim+eng', config=config)
        except pytesseract.TesseractError:
            return pytesseract.image_to_string(image, lang='eng', config=config)
    except ImportError as e:
        return f"[OCR 依赖未安装: {e}。请执行 pip install pytesseract Pillow PyMuPDF]"
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "[Tesseract OCR 引擎未安装。下载地址: https://github.com/UB-Mannheim/tesseract/releases]"
    except Exception as e:
        return f"[OCR 识别失败: {e}]"


def _preprocess_image(image):
    """图像预处理：OTSU 二值化 + 去噪，输出干净的黑白文字图"""
    try:
        import numpy as np

        # 转灰度
        if image.mode != 'L':
            image = image.convert('L')
        img_array = np.array(image)

        # 尝试用 OpenCV 做 OTSU 二值化（效果最好）
        try:
            import cv2
            # OTSU 自动阈值二值化：把文字和背景彻底分离
            _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # 中值滤波去噪：去除孤立噪点，保留文字笔画
            binary = cv2.medianBlur(binary, 3)
            return Image.fromarray(binary)
        except ImportError:
            pass

        # 回退：用 PIL 做手动阈值二值化
        # 计算 OTSU 阈值（纯 Python/numpy 实现）
        hist, _ = np.histogram(img_array.flatten(), bins=256, range=(0, 256))
        total = img_array.size
        sum_all = (np.arange(256) * hist).sum()
        weight_bg = 0
        sum_bg = 0
        max_var = 0
        threshold = 128
        for t in range(256):
            weight_bg += hist[t]
            if weight_bg == 0 or weight_bg == total:
                continue
            weight_fg = total - weight_bg
            sum_bg += t * hist[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_all - sum_bg) / weight_fg
            var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if var_between > max_var:
                max_var = var_between
                threshold = t
        # 应用阈值
        binary = np.where(img_array > threshold, 255, 0).astype(np.uint8)
        return Image.fromarray(binary)

    except Exception:
        # 最终回退
        if image.mode != 'L':
            image = image.convert('L')
        return image


def _auto_detect_tesseract():
    """自动探测 tesseract 安装路径并配置 pytesseract（结果缓存，只探测一次）"""
    import pytesseract

    # 已配置过则跳过
    if pytesseract.pytesseract.tesseract_cmd != 'tesseract':
        path = pytesseract.pytesseract.tesseract_cmd
        if path and os.path.exists(path):
            return True
        # 路径失效，重置后重新探测
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'

    import subprocess
    import platform

    system = platform.system()

    if system == 'Windows':
        candidates = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Tesseract-OCR', 'tesseract.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Tesseract-OCR', 'tesseract.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Tesseract-OCR', 'tesseract.exe'),
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'D:\Tesseract-OCR\tesseract.exe',
            r'E:\Tesseract-OCR\tesseract.exe',
        ]
        for p in candidates:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return
        try:
            result = subprocess.run(['where', 'tesseract'], capture_output=True,
                                   text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pytesseract.pytesseract.tesseract_cmd = result.stdout.strip().split('\n')[0]
        except Exception:
            pass
    else:
        for p in ['/usr/bin/tesseract', '/usr/local/bin/tesseract']:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return


def _normalize_ocr_text(text: str) -> str:
    """清洗 OCR 噪声，合并不当空格，修复常见分隔符，过滤乱码"""
    # 合并中文单字间的空格
    result = re.sub(r'([一-鿿])\s+([一-鿿])', r'\1\2', text)
    # 合并英文词内空格
    result = re.sub(r'([A-Za-z])\s+([A-Za-z])', r'\1\2', result)
    # 统一分隔符
    result = re.sub(r'[-—–]\s*', '至', result)
    # 合并多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    # 移除行首 OCR 乱码
    result = re.sub(r'^[。oO©·]\s*', '', result, flags=re.MULTILINE)
    # 修复常见 OCR 拆分
    for phrase in ['教育背景', '工作经历', '项目经验', '专业技能', '获奖与证书', '教育经历', '自我评价']:
        spaced = r'\s*'.join(list(phrase))
        result = re.sub(spaced, phrase, result)

    # 过滤重复乱码行：同一汉字连续出现 5 次以上（如 "阿巴阿巴阿巴"）
    def _has_garbage_repeat(line: str) -> bool:
        # 中文字符重复模式检测
        chars = re.findall(r'[一-鿿]', line)
        if len(chars) < 5:
            return False
        # 检查是否同一组字在反复出现
        unique = list(dict.fromkeys(chars))
        if len(unique) == 1:
            return True  # 全是同一个字
        if len(unique) <= 4 and len(chars) > 10:
            # 少量字符在高频重复
            return all(line.count(c) >= 3 for c in unique)
        return False

    # 过滤水印残留行：单行以特殊字符为主或中文过少
    def _is_noise_line(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        chinese = len(re.findall(r'[一-鿿]', stripped))
        total = len(stripped)
        # 中文字符占比低于 20% 且长度超过 10，可能是噪声
        if total > 10 and chinese / total < 0.2:
            return True
        # 长度少于 3 个有意义字符
        if chinese < 2 and total < 8:
            return True
        # 包含大量非打印字符或控制字符
        garbage_chars = len(re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', stripped))
        if garbage_chars > 2:
            return True
        return False

    lines = result.split('\n')
    cleaned = []
    for line in lines:
        if _has_garbage_repeat(line):
            continue
        if _is_noise_line(line):
            continue
        cleaned.append(line)
    result = '\n'.join(cleaned)
    # 再次合并多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    print("=" * 50)
    print("HR 智能招聘工具集（精简版）")
    print("=" * 50)

    # 测试数据加载
    print("\n[1] 测试简历加载...")
    test_txt = "assets/resume_std.txt"
    if os.path.exists(test_txt):
        text = load_resume_file(test_txt)
        print(f"  加载成功，{len(text)} 字符")
    else:
        print(f"  {test_txt} 不存在，跳过")

    # 测试知识参考
    print("\n[2] 测试评估框架...")
    guide = get_evaluation_guide()
    print(f"  评估框架: {len(guide)} 字符")

    print("\n[3] 测试风险清单...")
    checklist = get_risk_checklist()
    print(f"  风险清单: {len(checklist)} 字符")

    print("\n[4] 测试技能别名表...")
    aliases = get_skill_alias_map()
    print(f"  别名条目: {len(aliases)} 条")

    print("\n[5] 测试薪资查询...")
    salary = market_salary_query("AI应用实习生", "杭州", 0)
    print(salary)

    print("\n[6] 测试对比框架...")
    compare = get_compare_prompt(3)
    print(f"  对比框架: {len(compare)} 字符")

    print("\n[7] 测试报告框架...")
    report = get_report_prompt()
    print(f"  报告框架: {len(report)} 字符")

    print("\n" + "=" * 50)
    print("全部工具就绪")
    print("=" * 50)
