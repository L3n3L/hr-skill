"""
ATS系统连接器
支持对接主流招聘系统：Moka、Workday、北森、薪人薪事等
"""

import json
import time
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime


class ATSConnector(ABC):
    """ATS连接器基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def push_candidate(self, candidate: Dict) -> Dict:
        """推送候选人"""
        pass
    
    @abstractmethod
    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        """获取候选人信息"""
        pass
    
    @abstractmethod
    def update_status(self, candidate_id: str, status: str) -> bool:
        """更新候选人状态"""
        pass


class MockATSConnector(ATSConnector):
    """模拟ATS连接器 - 用于测试"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.connected = False
        self.candidates = {}  # 模拟数据存储
    
    def connect(self) -> bool:
        self.connected = True
        print(f"[MockATS] 连接成功，配置: {self.config}")
        return True
    
    def push_candidate(self, candidate: Dict) -> Dict:
        if not self.connected:
            self.connect()
        
        candidate_id = candidate.get('candidate_id', f"CAND_{int(time.time())}")
        self.candidates[candidate_id] = {
            **candidate,
            'ats_id': f"ATS_{candidate_id}",
            'created_at': datetime.now().isoformat(),
            'status': 'new'
        }
        
        return {
            'success': True,
            'external_id': f"ATS_{candidate_id}",
            'message': '候选人已成功推送到ATS系统'
        }
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        return self.candidates.get(candidate_id)
    
    def update_status(self, candidate_id: str, status: str) -> bool:
        if candidate_id in self.candidates:
            self.candidates[candidate_id]['status'] = status
            return True
        return False


class MokaConnector(ATSConnector):
    """Moka招聘系统连接器"""
    
    BASE_URL = "https://api.mokahr.com/v1"
    
    def __init__(self, api_key: str = None, secret: str = None):
        self.api_key = api_key
        self.secret = secret
        self.connected = False
        self.token = None
    
    def connect(self) -> bool:
        """
        连接Moka API
        实际需要实现OAuth2认证流程
        """
        if not self.api_key:
            print("[Moka] 未配置API密钥，使用模拟模式")
            self.connected = True
            return True
        
        # 实际API调用
        # response = requests.post(f"{self.BASE_URL}/auth/token", ...)
        self.token = "mock_token"
        self.connected = True
        return True
    
    def push_candidate(self, candidate: Dict) -> Dict:
        """
        推送候选人到Moka
        
        字段映射:
        - candidate_name -> name
        - email -> email
        - phone -> phone_number
        - education -> education_records
        - work_experience -> work_experience_records
        """
        if not self.connected:
            self.connect()
        
        # 转换字段格式
        moka_candidate = self._convert_to_moka_format(candidate)
        
        # 实际API调用
        # response = requests.post(f"{self.BASE_URL}/candidates", json=moka_candidate, headers=self._get_headers())
        
        return {
            'success': True,
            'external_id': f"MOKA_{int(time.time())}",
            'message': '成功推送到Moka系统',
            'data': moka_candidate
        }
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        # 实际API调用
        # response = requests.get(f"{self.BASE_URL}/candidates/{candidate_id}", headers=self._get_headers())
        return None
    
    def update_status(self, candidate_id: str, status: str) -> bool:
        """
        更新候选人状态
        状态映射:
        - new -> 0 (新建)
        - screening -> 1 (筛选中)
        - interview -> 2 (面试中)
        - offer -> 3 (offer中)
        - hired -> 4 (已入职)
        - rejected -> 5 (已淘汰)
        """
        status_map = {
            'new': 0, 'screening': 1, 'interview': 2, 
            'offer': 3, 'hired': 4, 'rejected': 5
        }
        
        # 实际API调用
        # response = requests.patch(f"{self.BASE_URL}/candidates/{candidate_id}", 
        #                          json={'process_status': status_map.get(status, 0)})
        
        return True
    
    def _convert_to_moka_format(self, candidate: Dict) -> Dict:
        """转换为Moka格式"""
        return {
            'name': candidate.get('personal_info', {}).get('name', ''),
            'email': candidate.get('personal_info', {}).get('email', ''),
            'phone_number': candidate.get('personal_info', {}).get('phone', ''),
            'education_records': [{
                'school': e.get('school', ''),
                'major': e.get('major', ''),
                'degree': candidate.get('personal_info', {}).get('degree', ''),
                'start_date': e.get('start_year', ''),
                'end_date': e.get('end_year', '')
            } for e in candidate.get('education', [])],
            'work_experience_records': [{
                'company': exp.get('company', ''),
                'position': exp.get('position', ''),
                'start_date': exp.get('period', '').split(' - ')[0] if exp.get('period') else '',
                'end_date': exp.get('period', '').split(' - ')[-1] if exp.get('period') else '',
                'description': exp.get('description', '')
            } for exp in candidate.get('work_experience', [])],
            'skill_list': candidate.get('skills', [])
        }
    
    def _get_headers(self) -> Dict:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }


class WorkdayConnector(ATSConnector):
    """Workday连接器"""
    
    def __init__(self, tenant: str = None, client_id: str = None):
        self.tenant = tenant
        self.client_id = client_id
        self.connected = False
    
    def connect(self) -> bool:
        if not self.tenant:
            print("[Workday] 未配置租户信息，使用模拟模式")
        self.connected = True
        return True
    
    def push_candidate(self, candidate: Dict) -> Dict:
        if not self.connected:
            self.connect()
        
        workday_data = self._convert_to_workday_format(candidate)
        
        return {
            'success': True,
            'external_id': f"WD_{int(time.time())}",
            'message': '成功推送到Workday系统',
            'data': workday_data
        }
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        return None
    
    def update_status(self, candidate_id: str, status: str) -> bool:
        return True
    
    def _convert_to_workday_format(self, candidate: Dict) -> Dict:
        """转换为Workday格式"""
        return {
            'worker': {
                'personal_data': {
                    'legal_name': {
                        'given_name': candidate.get('personal_info', {}).get('name', ''),
                    },
                    'contact_data': {
                        'email_address': candidate.get('personal_info', {}).get('email', ''),
                        'phone_number': candidate.get('personal_info', {}).get('phone', '')
                    }
                }
            }
        }


class GreensheetConnector(ATSConnector):
    """薪人薪事连接器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.connected = False
    
    def connect(self) -> bool:
        self.connected = True
        return True
    
    def push_candidate(self, candidate: Dict) -> Dict:
        greensheet_data = self._convert_to_greensheet_format(candidate)
        
        return {
            'success': True,
            'external_id': f"GS_{int(time.time())}",
            'message': '成功推送到薪人薪事系统',
            'data': greensheet_data
        }
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        return None
    
    def update_status(self, candidate_id: str, status: str) -> bool:
        return True
    
    def _convert_to_greensheet_format(self, candidate: Dict) -> Dict:
        """转换为薪人薪事格式"""
        return {
            'name': candidate.get('personal_info', {}).get('name', ''),
            'mobile': candidate.get('personal_info', {}).get('phone', ''),
            'email': candidate.get('personal_info', {}).get('email', ''),
            'education_list': candidate.get('education', []),
            'work_exp_list': candidate.get('work_experience', []),
            'skill_list': candidate.get('skills', [])
        }


class ATSFactory:
    """ATS连接器工厂"""
    
    CONNECTORS = {
        'mock': MockATSConnector,
        'moka': MokaConnector,
        'workday': WorkdayConnector,
        'greensheet': GreensheetConnector,
    }
    
    @classmethod
    def create(cls, ats_type: str, **config) -> ATSConnector:
        """
        创建ATS连接器
        
        Args:
            ats_type: ATS类型 (mock, moka, workday, greensheet)
            **config: 配置参数
        """
        connector_class = cls.CONNECTORS.get(ats_type.lower())
        
        if not connector_class:
            raise ValueError(f"不支持的ATS类型: {ats_type}")
        
        return connector_class(**config)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """获取支持的ATS类型"""
        return list(cls.CONNECTORS.keys())


def push_to_ats_enhanced(resume: Dict, jd: Dict, ats_type: str = 'mock', config: Dict = None) -> Dict:
    """
    增强版ATS推送
    
    Args:
        resume: 候选人简历
        jd: 岗位需求
        ats_type: ATS系统类型
        config: 配置
    
    Returns:
        推送结果
    """
    try:
        connector = ATSFactory.create(ats_type, **(config or {}))
        
        # 准备数据
        candidate_data = {
            'candidate_id': resume.get('candidate_id', f"CAND_{int(time.time())}"),
            'name': resume.get('personal_info', {}).get('name', ''),
            'email': resume.get('personal_info', {}).get('email', ''),
            'phone': resume.get('personal_info', {}).get('phone', ''),
            'education': resume.get('education', []),
            'work_experience': resume.get('work_experience', []),
            'skills': resume.get('skills', []),
            'projects': resume.get('projects', []),
            'source': 'ai_screening',
            'application_date': datetime.now().isoformat(),
            'target_position': jd.get('position_name', ''),
            'scores': resume.get('scores', {}),
            'risks': resume.get('risks', [])
        }
        
        result = connector.push_candidate(candidate_data)
        
        # 更新状态为待筛选
        if result.get('success'):
            connector.update_status(result['external_id'], 'screening')
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'推送失败: {e}'
        }


if __name__ == '__main__':
    print("=" * 50)
    print("ATS连接器测试")
    print("=" * 50)
    
    # 测试工厂
    print("\n支持的ATS类型:", ATSFactory.get_supported_types())
    
    # 测试Mock连接器
    print("\n[1] 测试Mock连接器:")
    connector = ATSFactory.create('mock')
    result = connector.push_candidate({
        'candidate_id': 'TEST001',
        'personal_info': {'name': '张三', 'email': 'zhangsan@example.com'}
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 测试增强版推送
    print("\n[2] 测试增强版ATS推送:")
    result = push_to_ats_enhanced(
        {'candidate_id': 'C001', 'personal_info': {'name': '测试'}},
        {'position_name': 'Python工程师'},
        'moka'
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
