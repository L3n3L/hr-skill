import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class ResumeParser:
    """简历解析器 - 提取关键信息"""
    
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'1[3-9]\d{9}',
            'age': r'(?:年龄|岁)[：:]?\s*(\d+)',
            'degree': r'(?:学历|学位)[：:]?\s*([初中高中大专本科硕士博士研究生]+)',
            'working_years': r'(?:工作年限|经验)[：:]?\s*(\d+)',
        }
    
    def parse(self, text: str) -> Dict:
        """解析简历文本"""
        result = {
            'personal_info': self._extract_personal_info(text),
            'education': self._extract_education(text),
            'work_experience': self._extract_work_experience(text),
            'skills': self._extract_skills(text),
            'projects': self._extract_projects(text),
        }
        return result
    
    def _extract_personal_info(self, text: str) -> Dict:
        """提取个人信息"""
        info = {}
        info['email'] = self._find_pattern(text, 'email')
        info['phone'] = self._find_pattern(text, 'phone')
        info['age'] = self._find_pattern(text, 'age')
        info['degree'] = self._find_pattern(text, 'degree')
        info['working_years'] = self._find_pattern(text, 'working_years')
        return info
    
    def _extract_education(self, text: str) -> List[Dict]:
        """提取教育经历"""
        education = []
        patterns = [
            r'(\d{4})\s*[-~]\s*(\d{4}|[至今]+)\s*[^|]*?([大学|学院|学校])[^|]*?\s*([^在|于|$]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                education.append({
                    'start_year': match[0],
                    'end_year': match[1],
                    'school': match[2] + match[3] if len(match) > 3 else '',
                    'major': '',
                })
        return education
    
    def _extract_work_experience(self, text: str) -> List[Dict]:
        """提取工作经历"""
        experiences = []
        sections = re.split(r'(?:工作经历|职业经历)', text)
        if len(sections) > 1:
            exp_text = sections[1]
            company_blocks = re.split(r'\d{4}[年.\-]\d{1,2}', exp_text)
            for block in company_blocks[1:]:
                if block.strip():
                    experiences.append({'description': block.strip()[:200]})
        return experiences
    
    def _extract_skills(self, text: str) -> List[str]:
        """提取技能"""
        skills = []
        skill_keywords = [
            'Python', 'Java', 'Go', 'JavaScript', 'TypeScript', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'Spring',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Kafka',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'Git', 'Linux', 'Nginx', 'TensorFlow', 'PyTorch',
        ]
        for skill in skill_keywords:
            if skill.lower() in text.lower():
                skills.append(skill)
        return skills
    
    def _extract_projects(self, text: str) -> List[Dict]:
        """提取项目经历"""
        projects = []
        sections = re.split(r'(?:项目经历|项目)', text)
        if len(sections) > 1:
            proj_text = sections[1]
            project_blocks = re.split(r'[-—–]\s*\d', proj_text)
            for block in project_blocks[1:]:
                if block.strip():
                    projects.append({'description': block.strip()[:300]})
        return projects
    
    def _find_pattern(self, text: str, pattern_name: str) -> Optional[str]:
        """查找匹配的模式"""
        pattern = self.patterns.get(pattern_name, '')
        if pattern:
            match = re.search(pattern, text)
            return match.group(1) if match else None
        return None
    
    def generate_summary(self, parsed_data: Dict) -> str:
        """生成简历摘要"""
        summary_parts = []
        
        # 基本信息
        personal = parsed_data.get('personal_info', {})
        if personal.get('degree'):
            summary_parts.append(f"学历: {personal['degree']}")
        if personal.get('working_years'):
            summary_parts.append(f"工作年限: {personal['working_years']}年")
        
        # 技能
        skills = parsed_data.get('skills', [])
        if skills:
            summary_parts.append(f"核心技能: {', '.join(skills[:8])}")
        
        # 经验
        experiences = parsed_data.get('work_experience', [])
        summary_parts.append(f"工作经历: {len(experiences)}段")
        
        # 项目
        projects = parsed_data.get('projects', [])
        summary_parts.append(f"项目经历: {len(projects)}个")
        
        return '\n'.join(summary_parts)


if __name__ == '__main__':
    parser = ResumeParser()
    
    # 测试
    sample_text = """
    姓名: 张三
    邮箱: zhangsan@example.com
    电话: 13800138000
    学历: 本科
    工作年限: 5年
    
    技能: Python, Java, MySQL, Docker, AWS
    
    工作经历:
    2020.03 - 至今 某互联网公司 高级后端工程师
    - 负责核心服务架构设计
    - 带领5人团队完成微服务改造
    
    项目经历:
    - 分布式缓存系统设计与实现
    - 日处理请求量1000万+
    """
    
    result = parser.parse(sample_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('\n=== 摘要 ===')
    print(parser.generate_summary(result))
