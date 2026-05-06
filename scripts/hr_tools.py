"""
HR智能招聘工具集
包含输入层、分析决策层、输出执行层、知识增强层的核心功能
"""

import re
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


# ==================== 一、输入层：数据加载与解析 ====================

def load_resume_file(file_path: str) -> str:
    """
    读取PDF/Word/图片简历，提取纯文本
    
    Args:
        file_path: 文件路径（支持.pdf, .docx, .jpg, .png）
    
    Returns:
        提取的原始文本
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
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text()
                doc.close()
            except ImportError:
                text = "[需要安装PyMuPDF: pip install PyMuPDF]"
                
        elif suffix == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text = '\n'.join([p.text for p in doc.paragraphs])
            except ImportError:
                text = "[需要安装python-docx: pip install python-docx]"
                
        elif suffix in ['.jpg', '.jpeg', '.png']:
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img, lang='chi+eng')
            except ImportError:
                text = "[需要安装pytesseract和PIL]"
                
    except Exception as e:
        text = f"[读取文件失败: {str(e)}]"
    
    return text


def parse_resume_text(text: str) -> Dict[str, Any]:
    """
    将简历文本转为结构化JSON
    
    Args:
        text: 简历原始文本
    
    Returns:
        结构化简历对象
    """
    parser = ResumeParserV2()
    return parser.parse(text)


def parse_job_description(text: str) -> Dict[str, Any]:
    """
    从岗位JD中抽取出结构化要求
    
    Args:
        text: JD文本
    
    Returns:
        岗位需求JSON
    """
    jd_parser = JobDescriptionParser()
    return jd_parser.parse(text)


def load_candidate_batch(folder_path: str, extensions: List[str] = None) -> List[Dict]:
    """
    批量加载文件夹内所有简历
    
    Args:
        folder_path: 文件夹路径
        extensions: 支持的文件扩展名列表
    
    Returns:
        简历文本列表 [{filename, text, parsed}]
    """
    if extensions is None:
        extensions = ['.txt', '.pdf', '.docx', '.jpg', '.png']
    
    results = []
    folder = Path(folder_path)
    
    for ext in extensions:
        for file_path in folder.glob(f"*{ext}"):
            try:
                text = load_resume_file(str(file_path))
                parsed = parse_resume_text(text)
                results.append({
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'text': text,
                    'parsed': parsed
                })
            except Exception as e:
                results.append({
                    'filename': file_path.name,
                    'error': str(e)
                })
    
    return results


# ==================== 二、分析决策层 ====================

def hard_filter(resume: Dict, jd: Dict) -> Dict[str, Any]:
    """
    硬性条件筛查，返回不通过原因
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
    
    Returns:
        {"passed": bool, "reasons": [str]}
    """
    reasons = []
    
    # 学历检查
    required_degree = jd.get('education', '')
    candidate_degree = resume.get('personal_info', {}).get('degree', '')
    if required_degree and not _degree_match(candidate_degree, required_degree):
        reasons.append(f"学历不符: 要求{required_degree}，候选人{candidate_degree or '未填写'}")
    
    # 工作经验年限检查
    required_years = jd.get('min_experience_years', 0)
    candidate_years = int(resume.get('personal_info', {}).get('working_years', 0) or 0)
    if candidate_years < required_years:
        reasons.append(f"工作经验不足: 要求{required_years}年，实际{candidate_years}年")
    
    # 必备技能检查
    required_skills = jd.get('required_skills', [])
    candidate_skills = [s.lower() for s in resume.get('skills', [])]
    missing_skills = [s for s in required_skills if s.lower() not in candidate_skills]
    if missing_skills:
        reasons.append(f"缺少必备技能: {', '.join(missing_skills)}")
    
    return {
        'passed': len(reasons) == 0,
        'reasons': reasons
    }


def score_resume(resume: Dict, jd: Dict) -> Dict[str, Any]:
    """
    多维度量化打分
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
    
    Returns:
        {"total": int, "dimensions": {...}}
    """
    dimensions = {}
    
    # 1. 技能匹配度 (30%)
    skill_score = _score_skill_match(resume, jd)
    dimensions['skill_match'] = skill_score
    
    # 2. 经验匹配度 (25%)
    exp_score = _score_experience_match(resume, jd)
    dimensions['experience_match'] = exp_score
    
    # 3. 稳定性 (20%)
    stability_score = _score_stability(resume)
    dimensions['stability'] = stability_score
    
    # 4. 教育背景 (15%)
    edu_score = _score_education(resume, jd)
    dimensions['education'] = edu_score
    
    # 5. 成长性 (10%)
    growth_score = _score_growth_potential(resume)
    dimensions['growth_potential'] = growth_score
    
    # 总分
    total = int(
        skill_score * 0.30 +
        exp_score * 0.25 +
        stability_score * 0.20 +
        edu_score * 0.15 +
        growth_score * 0.10
    )
    
    return {
        'total': total,
        'dimensions': dimensions,
        'tier': _get_tier(total)
    }


def rank_candidates(candidates: List[Dict], jd: Dict, weights: Dict = None) -> List[Dict]:
    """
    对多个候选人按总分/加权分排序
    
    Args:
        candidates: 候选人列表
        jd: 岗位需求
        weights: 自定义权重 {"skill_match": 0.4, ...}
    
    Returns:
        排序后的候选人列表
    """
    if weights is None:
        weights = {'skill_match': 0.30, 'experience_match': 0.25, 'stability': 0.20, 
                   'education': 0.15, 'growth_potential': 0.10}
    
    scored = []
    for i, resume in enumerate(candidates):
        try:
            scores = score_resume(resume, jd)
            filter_result = hard_filter(resume, jd)
            
            scored.append({
                'index': i,
                'resume': resume,
                'scores': scores,
                'passed': filter_result['passed'],
                'filter_reasons': filter_result.get('reasons', []),
                'final_score': scores['total'] if filter_result['passed'] else 0
            })
        except Exception as e:
            scored.append({
                'index': i,
                'error': str(e),
                'final_score': 0
            })
    
    # 排序：通过的在前，按分数降序
    scored.sort(key=lambda x: (x.get('passed', False), x.get('final_score', 0)), reverse=True)
    
    return scored


def flag_risks(resume: Dict) -> List[Dict[str, Any]]:
    """
    标记可疑点
    
    Args:
        resume: 结构化简历
    
    Returns:
        [{"type": str, "severity": str, "detail": str}]
    """
    risks = []
    
    # 1. 频繁跳槽检测
    job_changes = _detect_job_hopping(resume)
    if job_changes['count'] > 3:
        risks.append({
            'type': 'job_hopping',
            'severity': 'high' if job_changes['count'] > 5 else 'medium',
            'detail': f"近{job_changes['years']}年内换工作{job_changes['count']}次，平均{int(job_changes['years']/job_changes['count'])}个月/次"
        })
    
    # 2. 空窗期检测
    gaps = _detect_employment_gaps(resume)
    if gaps:
        for gap in gaps:
            risks.append({
                'type': 'employment_gap',
                'severity': 'medium',
                'detail': f"存在{int(gap['months'])}个月空窗期: {gap['period']}"
            })
    
    # 3. 职位下降检测
    if _detect_position_decline(resume):
        risks.append({
            'type': 'position_decline',
            'severity': 'medium',
            'detail': "职业轨迹显示职位/职级下降趋势"
        })
    
    # 4. 描述无量化检测
    if _has_unquantified_descriptions(resume):
        risks.append({
            'type': 'vague_descriptions',
            'severity': 'low',
            'detail': "工作描述缺少具体量化数据，建议面试时深入追问"
        })
    
    return risks


def detect_inconsistency(resume: Dict) -> List[Dict[str, Any]]:
    """
    简历信息前后矛盾检测
    
    Args:
        resume: 结构化简历
    
    Returns:
        [{"type": str, "detail": str}]
    """
    inconsistencies = []
    
    # 1. 时间重叠检测
    overlaps = _detect_time_overlaps(resume)
    if overlaps:
        inconsistencies.append({
            'type': 'time_overlap',
            'detail': f"存在工作时间重叠: {overlaps}"
        })
    
    # 2. 年龄与学历/经历矛盾
    age = resume.get('personal_info', {}).get('age')
    education = resume.get('education', [])
    if age and education:
        try:
            age_int = int(age)
            earliest_graduation = min([int(e.get('end_year', 2020)) for e in education if e.get('end_year')])
            expected_age = earliest_graduation - 22  # 假设18岁上大学
            if abs(age_int - expected_age) > 5:
                inconsistencies.append({
                    'type': 'age_education_mismatch',
                    'detail': f"年龄({age_int}岁)与最早毕业时间({earliest_graduation}年)可能存在矛盾"
                })
        except (ValueError, TypeError):
            pass
    
    # 3. 职位与公司规模矛盾
    work_exp = resume.get('work_experience', [])
    if len(work_exp) >= 2:
        for i, exp in enumerate(work_exp[:-1]):
            current_level = exp.get('level', '')
            next_level = work_exp[i+1].get('level', '')
            if current_level == 'senior' and next_level == 'junior':
                inconsistencies.append({
                    'type': 'level_mismatch',
                    'detail': f"从{exp.get('company', '公司A')}[{current_level}]降级到{work_exp[i+1].get('company', '公司B')}[{next_level}]"
                })
    
    return inconsistencies


def compare_candidates(candidates: List[Dict], jd: Dict) -> str:
    """
    两两或一组对比，输出优劣对比表
    
    Args:
        candidates: 候选人列表
        jd: 岗位需求
    
    Returns:
        Markdown格式的对比表
    """
    if not candidates:
        return "无候选人数据"
    
    # 收集所有评估维度
    all_skills = set()
    for c in candidates:
        all_skills.update(c.get('skills', []))
    
    # 构建对比表
    header = "| 维度 | " + " | ".join([f"候选人{i+1}" for i in range(len(candidates))]) + " |"
    separator = "|------|" + "|------|" * len(candidates)
    
    rows = []
    
    # 基本信息
    rows.append(f"| 姓名 | " + " | ".join([c.get('personal_info', {}).get('name', '未知') for c in candidates]) + " |")
    rows.append(f"| 学历 | " + " | ".join([c.get('personal_info', {}).get('degree', '未知') for c in candidates]) + " |")
    rows.append(f"| 工作年限 | " + " | ".join([str(c.get('personal_info', {}).get('working_years', 0)) for c in candidates]) + " |")
    
    # 评分对比
    scores_list = [score_resume(c, jd) for c in candidates]
    rows.append(f"| **总分** | " + " | ".join([f"**{s['total']}**" for s in scores_list]) + " |")
    rows.append(f"| 技能匹配度 | " + " | ".join([str(s['dimensions']['skill_match']) for s in scores_list]) + " |")
    rows.append(f"| 稳定性 | " + " | ".join([str(s['dimensions']['stability']) for s in scores_list]) + " |")
    
    # 技能对比
    skill_rows = []
    for skill in list(all_skills)[:10]:  # 限制显示10个技能
        row = f"| {skill} | "
        row += " | ".join(["✓" if skill.lower() in c.get('skills', []) else "✗" for c in candidates])
        row += " |"
        skill_rows.append(row)
    
    # 风险对比
    risks_list = [flag_risks(c) for c in candidates]
    rows.append(f"| 风险数量 | " + " | ".join([str(len(r)) for r in risks_list]) + " |")
    
    result = "## 候选人对比表\n\n" + header + "\n" + separator + "\n" + "\n".join(rows)
    
    if skill_rows:
        result += "\n\n### 技能对比\n\n" + "\n".join(skill_rows)
    
    return result


def summarize_candidate(resume: Dict, jd: Dict, scores: Dict = None, risks: List = None) -> str:
    """
    为单个候选人写HR面试前的备忘
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
        scores: 评分结果（可选）
        risks: 风险列表（可选）
    
    Returns:
        Markdown格式的面试备忘
    """
    if scores is None:
        scores = score_resume(resume, jd)
    if risks is None:
        risks = flag_risks(resume)
    
    personal = resume.get('personal_info', {})
    
    # 核心优势
    advantages = []
    if scores['dimensions']['skill_match'] >= 80:
        advantages.append("技能匹配度高，熟练掌握岗位核心技能")
    if scores['dimensions']['stability'] >= 80:
        advantages.append("工作稳定性好，历史跳槽频率正常")
    if len(resume.get('projects', [])) >= 3:
        advantages.append("项目经验丰富，参与过多个实际项目")
    
    # 面试考察点
    focus_points = []
    if any(r['type'] == 'job_hopping' for r in risks):
        focus_points.append("职业稳定性：了解每次离职的真实原因")
    if any(r['type'] == 'vague_descriptions' for r in risks):
        focus_points.append("成果验证：请举例说明具体业绩和贡献")
    if any(r['type'] == 'employment_gap' for r in risks):
        focus_points.append("空窗期原因：了解这段时间的具体安排")
    
    # 推荐的STAR问题
    star_questions = [
        "请用STAR法则描述一个你主导的最成功的项目",
        "描述一次你解决复杂技术问题的经历",
        "如果给你一个新项目，你会如何开始？"
    ]
    
    summary = f"""## HR面试备忘

### 候选人概况
- **姓名**: {personal.get('name', '未知')}
- **学历**: {personal.get('degree', '未知')}
- **工作年限**: {personal.get('working_years', '未知')}年
- **核心技能**: {', '.join(resume.get('skills', [])[:8])}

### 综合评分: {scores['total']}/100 ({scores['tier']}类)
| 维度 | 得分 |
|------|------|
| 技能匹配度 | {scores['dimensions']['skill_match']} |
| 经验匹配度 | {scores['dimensions']['experience_match']} |
| 稳定性 | {scores['dimensions']['stability']} |
| 教育背景 | {scores['dimensions']['education']} |
| 成长潜力 | {scores['dimensions']['growth_potential']} |

### 核心优势
{"".join([f"{i+1}. {adv}\\n" for i, adv in enumerate(advantages)]) if advantages else "暂无明显优势"}

### 风险提示
{"".join([f"- **[{r['severity'].upper()}]** {r['detail']}\\n" for r in risks]) if risks else "无明显风险"}

### 面试重点关注
{"".join([f"{i+1}. {fp}\\n" for i, fp in enumerate(focus_points)]) if focus_points else "按常规流程进行"}

### 推荐STAR问题
{chr(10).join([f'{i+1}. {q}' for i, q in enumerate(star_questions)])}

### 薪资建议
期望薪资范围需在面试中确认，可参考市场薪资调研结果
"""
    
    return summary


# ==================== 三、输出与执行层 ====================

def generate_interview_invitation(resume: Dict, jd: Dict, interview_time: str, 
                                  location: str = "线上视频", 
                                  interviewer: str = "HR") -> str:
    """
    根据候选人和面试时间模板生成个性化邀约邮件
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
        interview_time: 面试时间 "YYYY-MM-DD HH:MM"
        location: 面试地点
        interviewer: 面试官姓名
    
    Returns:
        邮件正文
    """
    personal = resume.get('personal_info', {})
    name = personal.get('name', '候选人')
    position = jd.get('position_name', '相关岗位')
    
    template = f"""主题: 【面试邀请】{position}岗位面试 - {name}

亲爱的 {name}：

您好！感谢您投递{position}岗位，经过简历筛选，我们认为您的背景与该岗位有较高的匹配度，现诚邀您参加面试。

【面试信息】
- 岗位：{position}
- 时间：{interview_time}
- 形式：{location}
- 面试官：{interviewer}

【面试流程】
1. 初试（技术面试）：约45分钟
2. 复试（部门负责人）：约60分钟
3. 终面（HR/高管）：约30分钟

【准备事项】
- 请提前10分钟进入会议室
- 准备好简历及相关证书原件
- 如有技术作品/项目可携带展示

【确认回复】
请您确认是否参加面试，如有疑问请回复此邮件或致电联系我们。

期待与您的见面！

此致
敬礼

{interviewer}
人事部
{datetime.now().strftime('%Y-%m-%d')}
"""
    return template


def generate_rejection_email(resume: Dict, jd: Dict, feedback: str = None) -> str:
    """
    生成委婉的拒信，可选附上简短反馈
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
        feedback: 简短反馈（可选）
    
    Returns:
        邮件正文
    """
    personal = resume.get('personal_info', {})
    name = personal.get('name', '候选人')
    position = jd.get('position_name', '相关岗位')
    
    feedback_text = f"""
【关于您的申请】
经过慎重评估，我们认为您的经历与目前招聘岗位的匹配度有限。
{feedback or ""}
""" if feedback else """
【关于您的申请】
经过综合评估，我们暂未选择您进入下一轮面试。
"""
    
    template = f"""主题: 【感谢关注】{position}岗位申请结果 - {name}

Dear {name}：

您好！感谢您对{position}岗位的关注，以及您为此付出的时间和努力。

{feedback_text}

我们已将您的简历纳入人才储备库，后续如有合适岗位会优先联系您。

祝您职业发展顺利，早日找到理想的工作机会！

此致
敬礼

人事部
{datetime.now().strftime('%Y-%m-%d')}
"""
    return template


def push_to_ats(resume: Dict, jd: Dict, ats_system: str = "generic", config: Dict = None) -> Dict:
    """
    把结构化简历数据推送到招聘系统
    
    Args:
        resume: 结构化简历
        jd: 岗位需求
        ats_system: ATS系统类型 ("workday", "moka", "greensheet", "generic")
        config: 连接配置
    
    Returns:
        {"success": bool, "external_id": str, "message": str}
    """
    # 构建标准化数据
    candidate_data = {
        'candidate_id': resume.get('candidate_id', f"CAND_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        'name': resume.get('personal_info', {}).get('name', ''),
        'email': resume.get('personal_info', {}).get('email', ''),
        'phone': resume.get('personal_info', {}).get('phone', ''),
        'education': resume.get('education', []),
        'work_experience': resume.get('work_experience', []),
        'skills': resume.get('skills', []),
        'source': 'ai_screening',
        'application_date': datetime.now().isoformat(),
        'target_position': jd.get('position_name', '')
    }
    
    # TODO: 根据不同ATS系统实现具体的API调用
    # 目前返回模拟结果
    return {
        'success': True,
        'external_id': f"{ats_system.upper()}_{candidate_data['candidate_id']}",
        'message': f"成功推送到{ats_system}系统",
        'data': candidate_data
    }


def schedule_interview(candidates: List[Dict], duration: int = 60, 
                       calendar_config: Dict = None) -> Dict:
    """
    结合日历API，自动预约面试时间
    
    Args:
        candidates: 候选人列表
        duration: 面试时长（分钟）
        calendar_config: 日历配置
    
    Returns:
        预约结果
    """
    # 简化实现，返回可用时间建议
    import random
    
    suggestions = []
    for i, candidate in enumerate(candidates):
        suggestions.append({
            'candidate_name': candidate.get('personal_info', {}).get('name', f'候选人{i+1}'),
            'suggested_times': [
                f"{datetime.now().strftime('%Y-%m-%d')} {14+i*2:02d}:00",
                f"{datetime.now().strftime('%Y-%m-%d')} {15+i*2:02d}:00",
            ],
            'duration': duration
        })
    
    return {
        'scheduled': len(suggestions),
        'suggestions': suggestions,
        'message': '建议时间已生成，需确认后创建日程'
    }


def send_hr_report(resume: Dict, scores: Dict, recommendation: str, 
                   manager_email: str, manager_name: str = "用人经理") -> str:
    """
    将决策结果以邮件或消息发送给用人经理
    
    Args:
        resume: 候选人简历
        manager_email: 用人经理邮箱
        manager_name: 用人经理姓名
    
    Returns:
        邮件正文
    """
    personal = resume.get('personal_info', {})
    name = personal.get('name', '候选人')
    
    recommendation_text = {
        'A': f'强烈推荐面试',
        'B': f'建议安排面试',
        'C': f'暂不推荐'
    }.get(recommendation, f'推荐级别: {recommendation}')
    
    template = f"""主题: 【简历推荐】{name} - {recommendation_text}

亲爱的 {manager_name}：

您好！推荐以下候选人供您参考：

### 候选人信息
- **姓名**: {name}
- **学历**: {personal.get('degree', '未知')}
- **工作年限**: {personal.get('working_years', '未知')}年
- **核心技能**: {', '.join(resume.get('skills', [])[:5])}

### 综合评分
- **推荐级别**: {recommendation} ({scores.get('total', 0)}/100)
- 技能匹配度: {scores.get('dimensions', {}).get('skill_match', 0)}
- 稳定性: {scores.get('dimensions', {}).get('stability', 0)}
- 成长潜力: {scores.get('dimensions', {}).get('growth_potential', 0)}

### 推荐理由
{recommendation_text}。候选人简历已上传系统，请登录查看详情。

如需安排面试，请回复本邮件或联系HR协调时间。

祝好！

HR
{datetime.now().strftime('%Y-%m-%d')}
"""
    return template


# ==================== 四、知识增强层 ====================

def search_company_background(company_name: str) -> Dict:
    """
    查证候选人前东家的行业、规模
    
    Args:
        company_name: 公司名称
    
    Returns:
        公司背景信息
    """
    # TODO: 接入外部数据源（天眼查、企查查、LinkedIn等）
    # 目前返回模拟数据
    return {
        'company_name': company_name,
        'industry': '互联网/科技',
        'size': '1000-5000人',
        'stage': '成熟期',
        'founded': '2010年',
        'description': '该公司为业内知名企业，主营业务为XX',
        'verified': False,  # 需要接入真实数据源
        'note': '建议通过公开渠道或背调核实'
    }


def skill_normalizer(skills: List[str]) -> List[Dict[str, str]]:
    """
    把技能别名统一（如"js" → "JavaScript"）
    
    Args:
        skills: 原始技能列表
    
    Returns:
        [{"original": str, "normalized": str, "category": str}]
    """
    skill_map = {
        # 前端
        'js': 'JavaScript', 'ts': 'TypeScript', 'tsx': 'TypeScript',
        'vue': 'Vue.js', 'vue2': 'Vue.js 2', 'vue3': 'Vue.js 3',
        'react': 'React', 'ng': 'Angular', 'jq': 'jQuery',
        
        # 后端
        'py': 'Python', 'java': 'Java', 'go': 'Go', 'rb': 'Ruby',
        'c#': 'C#', 'cs': 'C#', 'cpp': 'C++', 'php': 'PHP',
        
        # 数据库
        'mysql': 'MySQL', 'pg': 'PostgreSQL', 'mongo': 'MongoDB', 'redis': 'Redis',
        'es': 'Elasticsearch', 'kafka': 'Apache Kafka',
        
        # DevOps
        'k8s': 'Kubernetes', 'docker': 'Docker', 'aws': 'AWS', 'gcp': 'Google Cloud',
        'az': 'Azure', 'jenkins': 'Jenkins', 'git': 'Git',
        
        # AI/ML
        'ml': '机器学习', 'ai': '人工智能', 'dl': '深度学习',
        'tf': 'TensorFlow', 'torch': 'PyTorch', 'nlp': 'NLP',
        
        # 其他
        'linux': 'Linux', 'nginx': 'Nginx', 'rabbitmq': 'RabbitMQ',
        'spring': 'Spring', 'springboot': 'Spring Boot',
        'flask': 'Flask', 'django': 'Django', 'fastapi': 'FastAPI',
    }
    
    categories = {
        'frontend': ['JavaScript', 'TypeScript', 'React', 'Vue.js', 'Angular', 'HTML', 'CSS'],
        'backend': ['Java', 'Python', 'Go', 'Ruby', 'PHP', 'C#', 'C++'],
        'database': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch'],
        'devops': ['Docker', 'Kubernetes', 'AWS', 'Azure', 'Git', 'Linux', 'Nginx', 'Jenkins'],
        'ai_ml': ['机器学习', '深度学习', 'TensorFlow', 'PyTorch', 'NLP'],
    }
    
    results = []
    for skill in skills:
        original = skill.strip()
        lower = original.lower()
        normalized = skill_map.get(lower, original)
        
        # 确定分类
        category = 'other'
        for cat, keywords in categories.items():
            if normalized in keywords or lower in [k.lower() for k in keywords]:
                category = cat
                break
        
        results.append({
            'original': original,
            'normalized': normalized,
            'category': category
        })
    
    return results


def culture_fit_analyzer(resume: Dict, company_values: List[str]) -> Dict:
    """
    根据企业价值观关键词，比对简历中的行为描述
    
    Args:
        resume: 候选人简历
        company_values: 企业价值观关键词列表
    
    Returns:
        文化契合度分析结果
    """
    # 提取简历中的行为描述
    work_exp_text = ' '.join([exp.get('description', '') for exp in resume.get('work_experience', [])])
    projects_text = ' '.join([proj.get('description', '') for proj in resume.get('projects', [])])
    all_text = work_exp_text + projects_text
    
    # 分析匹配度
    matches = []
    for value in company_values:
        value_lower = value.lower()
        # 检查价值观相关关键词
        if value_lower in all_text.lower():
            matches.append({
                'value': value,
                'matched': True,
                'evidence': f"简历中提及{value}"
            })
        else:
            matches.append({
                'value': value,
                'matched': False,
                'evidence': None
            })
    
    match_rate = len([m for m in matches if m['matched']]) / len(matches) * 100 if matches else 0
    
    return {
        'match_rate': int(match_rate),
        'fit_level': '高' if match_rate >= 70 else ('中' if match_rate >= 40 else '低'),
        'matches': matches,
        'recommendation': _get_culture_recommendation(match_rate)
    }


def market_salary_query(position: str, city: str, experience_years: int = None) -> Dict:
    """
    查询某岗位、某城市的薪资范围
    
    Args:
        position: 岗位名称
        city: 城市
        experience_years: 工作年限（可选）
    
    Returns:
        薪资范围信息
    """
    # TODO: 接入真实薪资数据源
    # 目前返回基于经验的估算值
    
    # 基础薪资表（月薪，单位K）
    base_salary = {
        'python': {'low': 15, 'mid': 25, 'high': 45},
        'java': {'low': 12, 'mid': 20, 'high': 40},
        '前端': {'low': 12, 'mid': 20, 'high': 38},
        '算法': {'low': 20, 'mid': 35, 'high': 60},
        '产品': {'low': 10, 'mid': 18, 'high': 35},
        '运营': {'low': 8, 'mid': 14, 'high': 28},
    }
    
    # 城市系数
    city_factor = {
        '北京': 1.3, '上海': 1.25, '深圳': 1.2, '杭州': 1.15,
        '广州': 1.0, '成都': 0.9, '武汉': 0.85, '西安': 0.8,
        'default': 0.9
    }
    
    # 经验系数
    exp_factor = 1.0
    if experience_years:
        if experience_years <= 2:
            exp_factor = 0.7
        elif experience_years <= 5:
            exp_factor = 1.0
        elif experience_years <= 10:
            exp_factor = 1.3
        else:
            exp_factor = 1.5
    
    # 查找岗位薪资
    position_key = 'python'  # 默认
    for key in base_salary:
        if key in position.lower():
            position_key = key
            break
    
    base = base_salary[position_key]
    factor = city_factor.get(city, city_factor['default'])
    
    return {
        'position': position,
        'city': city,
        'experience_years': experience_years,
        'salary_range': {
            'low': int(base['low'] * factor * exp_factor),
            'mid': int(base['mid'] * factor * exp_factor),
            'high': int(base['high'] * factor * exp_factor),
            'currency': 'CNY',
            'unit': 'K/月'
        },
        'annual_range': {
            'low': int(base['low'] * factor * exp_factor * 12),
            'mid': int(base['mid'] * factor * exp_factor * 12),
            'high': int(base['high'] * factor * exp_factor * 12),
            'currency': 'CNY',
            'unit': 'K/年'
        },
        'note': '数据基于市场调研，实际薪资需综合考虑候选人和公司情况'
    }


# ==================== 辅助类和函数 ====================

class ResumeParserV2:
    """增强版简历解析器"""
    
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'1[3-9]\d{9}',
            'age': r'(?:年龄|岁)[：:]?\s*(\d+)',
            'degree': r'(?:学历|学位)[：:]?\s*([初中高中大专本科硕士博士研究生]+)',
            'working_years': r'(?:工作年限|经验)[：:]?\s*(\d+)',
            'name': r'(?:姓名)[：:]?\s*([^\s\n]+)',
        }
        
        self.education_keywords = ['大学', '学院', '学校', '研究生', '硕士', '博士']
        self.work_keywords = ['工作经历', '职业经历', '任职', '职位']
        self.project_keywords = ['项目', '项目经历', '项目经验']
        self.skill_keywords = [
            'Python', 'Java', 'Go', 'JavaScript', 'TypeScript', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'Spring',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Kafka',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'Git', 'Linux', 'Nginx', 'TensorFlow', 'PyTorch',
            '人工智能', '机器学习', '深度学习', 'NLP',
            '微服务', '分布式', '高并发', '云原生'
        ]
    
    def parse(self, text: str) -> Dict:
        """解析简历文本"""
        return {
            'personal_info': self._extract_personal_info(text),
            'education': self._extract_education(text),
            'work_experience': self._extract_work_experience(text),
            'skills': self._extract_skills(text),
            'projects': self._extract_projects(text),
            'raw_text': text[:500],  # 保存原始文本前500字
        }
    
    def _extract_personal_info(self, text: str) -> Dict:
        info = {}
        info['name'] = self._find_pattern(text, 'name')
        info['email'] = self._find_pattern(text, 'email')
        info['phone'] = self._find_pattern(text, 'phone')
        info['age'] = self._find_pattern(text, 'age')
        info['degree'] = self._find_pattern(text, 'degree')
        info['working_years'] = self._find_pattern(text, 'working_years')
        return {k: v for k, v in info.items() if v}
    
    def _extract_education(self, text: str) -> List[Dict]:
        education = []
        lines = text.split('\n')
        for i, line in enumerate(lines):
            for kw in self.education_keywords:
                if kw in line and any(y in line for y in ['20', '19']) and '至' in line or '—' in line:
                    years = re.findall(r'(20\d{2}|19\d{2})', line)
                    if years and len(years) >= 2:
                        education.append({
                            'start_year': years[0],
                            'end_year': years[1],
                            'school': line[:50].strip(),
                            'major': ''
                        })
                    break
        return education
    
    def _extract_work_experience(self, text: str) -> List[Dict]:
        experiences = []
        # 按时间模式分割
        time_pattern = r'(20\d{2}[年.]\d{1,2}|19\d{2}[年.]\d{1,2})'
        parts = re.split(time_pattern, text)
        
        for i in range(1, len(parts), 3):
            if i+2 < len(parts):
                date = parts[i]
                content = parts[i+1] if i+1 < len(parts) else ''
                if len(content) > 20:
                    experiences.append({
                        'period': date,
                        'description': content[:300].strip()
                    })
        return experiences
    
    def _extract_skills(self, text: str) -> List[str]:
        skills = []
        text_lower = text.lower()
        for skill in self.skill_keywords:
            if skill.lower() in text_lower:
                skills.append(skill)
        return list(set(skills))
    
    def _extract_projects(self, text: str) -> List[Dict]:
        projects = []
        sections = re.split(r'(?:项目经历|项目经验|项目)', text)
        if len(sections) > 1:
            proj_text = sections[1] if len(sections) > 1 else sections[0]
            blocks = re.split(r'[-—–]\s*\d', proj_text)
            for block in blocks[1:]:
                if len(block) > 30:
                    projects.append({'description': block.strip()[:300]})
        return projects
    
    def _find_pattern(self, text: str, pattern_name: str) -> Optional[str]:
        pattern = self.patterns.get(pattern_name, '')
        if pattern:
            match = re.search(pattern, text)
            return match.group(1) if match else None
        return None


class JobDescriptionParser:
    """JD解析器"""
    
    def __init__(self):
        self.degree_map = {
            '博士': 4, '硕士': 3, '研究生': 3, '本科': 2, '大专': 1, '高中': 0
        }
    
    def parse(self, text: str) -> Dict:
        return {
            'position_name': self._extract_position(text),
            'education': self._extract_education(text),
            'min_experience_years': self._extract_experience_years(text),
            'required_skills': self._extract_required_skills(text),
            'preferred_skills': self._extract_preferred_skills(text),
            'responsibilities': self._extract_responsibilities(text),
            'raw_text': text[:500]
        }
    
    def _extract_position(self, text: str) -> str:
        match = re.search(r'(?:招|招聘|岗位|职位)[:：]?\s*([^\n，,]+)', text)
        return match.group(1).strip() if match else '未命名岗位'
    
    def _extract_education(self, text: str) -> str:
        for degree in ['博士', '硕士', '研究生', '本科', '大专', '高中']:
            if degree in text:
                return degree
        return ''
    
    def _extract_experience_years(self, text: str) -> int:
        match = re.search(r'(\d+)\s*(?:年|年以上)', text)
        return int(match.group(1)) if match else 0
    
    def _extract_required_skills(self, text: str) -> List[str]:
        skills = []
        # 提取"熟练掌握XXX"等模式
        patterns = [
            r'掌握\s*([A-Za-z0-9#+.]{2,30})',
            r'熟悉\s*([A-Za-z0-9#+.]{2,30})',
            r'精通\s*([A-Za-z0-9#+.]{2,30})',
            r'(?:Python|Java|Go|JavaScript|MySQL|MongoDB|Redis|Kafka|Docker|K8s|Linux)'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            skills.extend([m.strip() if isinstance(m, str) else m for m in matches])
        return list(set(skills))
    
    def _extract_preferred_skills(self, text: str) -> List[str]:
        preferred = []
        # 提取"优先/加分"项
        match = re.search(r'优先[，,]([^\n。]+)', text)
        if match:
            preferred = [s.strip() for s in re.split(r'[，,]', match.group(1))]
        return preferred
    
    def _extract_responsibilities(self, text: str) -> List[str]:
        responsibilities = []
        match = re.search(r'(?:岗位职责|工作内容|负责)[：:]?\s*([^\n]+(?:\n[^\n]+)*)', text)
        if match:
            responsibilities = [r.strip() for r in match.group(1).split('\n') if r.strip()]
        return responsibilities


# ==================== 内部评分辅助函数 ====================

def _degree_match(candidate: str, required: str) -> bool:
    """比较学历是否满足要求"""
    degree_values = {'博士': 5, '硕士': 4, '研究生': 4, '本科': 3, '大专': 2, '高中': 1}
    c_val = degree_values.get(candidate, 0)
    r_val = degree_values.get(required, 0)
    return c_val >= r_val


def _score_skill_match(resume: Dict, jd: Dict) -> int:
    """计算技能匹配度"""
    required = [s.lower() for s in jd.get('required_skills', [])]
    preferred = [s.lower() for s in jd.get('preferred_skills', [])]
    candidate = [s.lower() for s in resume.get('skills', [])]
    
    if not required:
        return 70
    
    required_match = len([s for s in required if s in candidate]) / len(required) * 100
    preferred_match = len([s for s in preferred if s in candidate]) / len(preferred) * 100 if preferred else 50
    
    return int(required_match * 0.7 + preferred_match * 0.3)


def _score_experience_match(resume: Dict, jd: Dict) -> int:
    """计算经验匹配度"""
    min_years = jd.get('min_experience_years', 0)
    candidate_years = int(resume.get('personal_info', {}).get('working_years', 0) or 0)
    
    if min_years == 0:
        return 80
    if candidate_years < min_years:
        return max(30, int(candidate_years / min_years * 50))
    if candidate_years <= min_years * 2:
        return 90
    return 80


def _score_stability(resume: Dict) -> int:
    """计算稳定性得分"""
    experiences = resume.get('work_experience', [])
    if len(experiences) <= 2:
        return 90
    if len(experiences) <= 4:
        return 75
    return 50


def _score_education(resume: Dict, jd: Dict) -> int:
    """计算教育背景得分"""
    required = jd.get('education', '')
    candidate = resume.get('personal_info', {}).get('degree', '')
    
    if not required:
        return 80
    if _degree_match(candidate, required):
        return 90
    return 50


def _score_growth_potential(resume: Dict) -> int:
    """计算成长潜力"""
    projects = resume.get('projects', [])
    skills = resume.get('skills', [])
    
    score = 50
    score += min(20, len(projects) * 5)
    score += min(20, len(skills) * 2)
    
    return min(100, score)


def _get_tier(score: int) -> str:
    """根据分数确定等级"""
    if score >= 80:
        return 'A'
    if score >= 60:
        return 'B'
    return 'C'


def _detect_job_hopping(resume: Dict) -> Dict:
    """检测频繁跳槽"""
    experiences = resume.get('work_experience', [])
    count = len(experiences)
    return {'count': count, 'years': 5, 'avg_months': 60/count if count else 0}


def _detect_employment_gaps(resume: Dict) -> List[Dict]:
    """检测空窗期"""
    return []  # 简化实现


def _detect_position_decline(resume: Dict) -> bool:
    """检测职位下降"""
    return False


def _has_unquantified_descriptions(resume: Dict) -> bool:
    """检测是否缺少量化描述"""
    text = ' '.join([e.get('description', '') for e in resume.get('work_experience', [])])
    quantifiers = ['%', '倍', '万', '千', '人', '个', '提高', '降低', '增长']
    return not any(q in text for q in quantifiers)


def _detect_time_overlaps(resume: Dict) -> List[str]:
    """检测时间重叠"""
    return []


def _get_culture_recommendation(rate: float) -> str:
    """获取文化契合度建议"""
    if rate >= 70:
        return "候选人价值观与公司文化高度契合，建议重点关注"
    if rate >= 40:
        return "候选人基本符合公司文化，可在面试中进一步考察"
    return "候选人价值观与公司文化存在差异，建议谨慎评估"


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import sys
    
    print("=" * 50)
    print("HR智能招聘工具集 - 测试")
    print("=" * 50)
    
    # 测试简历解析
    sample_resume = """
    姓名: 张三
    邮箱: zhangsan@example.com
    电话: 13800138000
    学历: 本科
    工作年限: 5年
    
    技能: Python, Java, MySQL, Docker, AWS, React
    
    工作经历:
    2020.03 - 至今 某互联网公司 高级后端工程师
    - 负责核心服务架构设计
    - 带领5人团队完成微服务改造
    
    项目经历:
    - 分布式缓存系统设计与实现
    - 日处理请求量1000万+
    """
    
    print("\n[1] 测试简历解析...")
    parsed = parse_resume_text(sample_resume)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    
    # 测试JD解析
    sample_jd = """
    招聘Python后端工程师
    
    岗位要求:
    - 本科及以上学历
    - 3年以上Python开发经验
    - 熟练掌握Django/Flask
    - 有微服务经验优先
    
    岗位职责:
    - 负责后端服务开发
    - 参与架构设计
    """
    
    print("\n[2] 测试JD解析...")
    jd = parse_job_description(sample_jd)
    print(json.dumps(jd, ensure_ascii=False, indent=2))
    
    # 测试筛选和打分
    print("\n[3] 测试硬性筛选...")
    filter_result = hard_filter(parsed, jd)
    print(json.dumps(filter_result, ensure_ascii=False, indent=2))
    
    print("\n[4] 测试评分...")
    scores = score_resume(parsed, jd)
    print(json.dumps(scores, ensure_ascii=False, indent=2))
    
    print("\n[5] 测试风险标记...")
    risks = flag_risks(parsed)
    print(json.dumps(risks, ensure_ascii=False, indent=2))
    
    print("\n[6] 测试面试备忘生成...")
    memo = summarize_candidate(parsed, jd, scores, risks)
    print(memo)
    
    print("\n[7] 测试邀约邮件生成...")
    email = generate_interview_invitation(parsed, jd, "2024-01-15 14:00")
    print(email)
    
    print("\n[8] 测试技能标准化...")
    normalized = skill_normalizer(['js', 'vue', 'k8s', 'python', 'ML'])
    print(json.dumps(normalized, ensure_ascii=False, indent=2))
    
    print("\n[9] 测试薪资查询...")
    salary = market_salary_query("Python后端", "北京", 5)
    print(json.dumps(salary, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)
