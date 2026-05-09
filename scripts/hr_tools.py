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
                         extensions: List[str] = None) -> List[Dict]:
    """
    批量加载文件夹内所有简历

    Args:
        folder_path: 文件夹路径
        extensions: 支持的文件扩展名，默认 ['.txt', '.pdf', '.docx', '.jpg', '.png']

    Returns:
        [{'filename': str, 'text': str, 'error': str|None}]
    """
    if extensions is None:
        extensions = ['.txt', '.pdf', '.docx', '.jpg', '.png']

    results = []
    folder = Path(folder_path)

    for ext in extensions:
        for file_path in folder.glob(f"*{ext}"):
            try:
                text = load_resume_file(str(file_path))
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


# ==================== 内部辅助函数 ====================

def _ocr_pdf_page(page) -> str:
    """对 PDF 页面进行 OCR 识别"""
    try:
        import fitz as _fitz
        import pytesseract
        from PIL import Image
        import io

        _auto_detect_tesseract()

        mat = _fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        try:
            return pytesseract.image_to_string(image, lang='chi_sim+eng')
        except pytesseract.TesseractError:
            return pytesseract.image_to_string(image, lang='eng')
    except ImportError as e:
        return f"[OCR 依赖未安装: {e}。请执行 pip install pytesseract Pillow PyMuPDF]"
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "[Tesseract OCR 引擎未安装。下载地址: https://github.com/UB-Mannheim/tesseract/releases]"
    except Exception as e:
        return f"[OCR 识别失败: {e}]"


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
    """清洗 OCR 噪声，合并不当空格，修复常见分隔符"""
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
    for phrase in ['教育背景', '工作经历', '项目经验', '专业技能', '获奖与证书']:
        spaced = r'\s*'.join(list(phrase))
        result = re.sub(spaced, phrase, result)
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
