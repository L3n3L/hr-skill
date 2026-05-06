"""
邮件生成器
生成各种HR相关邮件：面试邀请、拒信、offer通知等
"""

from typing import Dict, Optional
from datetime import datetime, timedelta


class EmailTemplate:
    """邮件模板类"""
    
    @staticmethod
    def interview_invitation(
        candidate_name: str,
        position: str,
        interview_time: str,
        interview_type: str = "视频面试",
        interviewer_name: str = "HR",
        additional_notes: str = ""
    ) -> str:
        """
        生成面试邀请邮件
        
        Args:
            candidate_name: 候选人姓名
            position: 岗位名称
            interview_time: 面试时间
            interview_type: 面试形式
            interviewer_name: 面试官姓名
            additional_notes: 附加说明
        """
        template = f"""主题: 【面试邀请】{position}岗位面试 - {candidate_name}

{candidate_name}，您好！

非常感谢您投递{position}岗位，经过简历筛选，我们认为您的背景与该岗位有较高的匹配度，现诚邀您参加面试。

【面试信息】
━━━━━━━━━━━━━━━━━━━━
• 岗位：{position}
• 时间：{interview_time}
• 形式：{interview_type}
• 面试官：{interviewer_name}
━━━━━━━━━━━━━━━━━━━━

【面试流程】
1. 初试（技术面试）：约45分钟
2. 复试（部门负责人）：约60分钟  
3. 终面（HR/高管）：约30分钟

【准备事项】
• 请提前10分钟进入会议室
• 准备好简历及相关证书原件
• 如有技术作品/项目可携带展示

{additional_notes}

【确认回复】
请您确认是否参加面试，如有疑问请回复此邮件或致电联系我们。

期待与您的见面！

此致
敬礼

{interviewer_name}
人事部
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template
    
    @staticmethod
    def rejection_email(
        candidate_name: str,
        position: str,
        feedback: Optional[str] = None,
        keep_in_touch: bool = True
    ) -> str:
        """
        生成拒绝邮件
        
        Args:
            candidate_name: 候选人姓名
            position: 岗位名称
            feedback: 简短反馈
            keep_in_touch: 是否保持联系
        """
        feedback_section = ""
        if feedback:
            feedback_section = f"""
【关于您的申请】
{feedback}
"""
        
        keep_section = """
我们已将您的简历纳入人才储备库，后续如有合适岗位会优先联系您。

祝您职业发展顺利，早日找到理想的工作机会！
""" if keep_in_touch else """
感谢您的理解与支持，祝您职业发展顺利！
"""
        
        template = f"""主题: 【感谢关注】{position}岗位申请结果 - {candidate_name}

{candidate_name}，您好！

感谢您对{position}岗位的关注，以及您为此付出的时间和努力。

{feedback_section}
{keep_section}
此致
敬礼

人事部
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template
    
    @staticmethod
    def offer_letter(
        candidate_name: str,
        position: str,
        department: str,
        entry_date: str,
        salary: str,
        probation_salary: str,
        benefits: str = ""
    ) -> str:
        """
        生成Offer Letter
        
        Args:
            candidate_name: 候选人姓名
            position: 岗位名称
            department: 部门
            entry_date: 入职日期
            salary: 正式薪资
            probation_salary: 试用期薪资
            benefits: 福利说明
        """
        template = f"""主题: 【录用通知】{position}岗位Offer - {candidate_name}

{candidate_name}，您好！

经过多轮面试，我们非常高兴地通知您，您已被正式录用！

【录用信息】
━━━━━━━━━━━━━━━━━━━━
• 岗位：{position}
• 部门：{department}
• 入职日期：{entry_date}
• 薪资：{salary}/月
• 试用期薪资：{probation_salary}/月
━━━━━━━━━━━━━━━━━━━━

【福利待遇】
{benefits if benefits else "• 五险一金\n• 带薪年假\n• 弹性工作\n• 定期体检\n• 团建活动"}

【注意事项】
1. 请于收到Offer后3个工作日内回复确认
2. 入职时请携带身份证、学历证书、离职证明等原件
3. 如有特殊情况无法按期入职，请提前与我联系

如有任何问题，欢迎随时联系我。

期待您的加入！

此致
敬礼

HR
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template
    
    @staticmethod
    def second_interview_invitation(
        candidate_name: str,
        position: str,
        interview_time: str,
        interviewer_name: str,
        interviewer_title: str,
        interview_focus: str = ""
    ) -> str:
        """
        生成二面邀请邮件
        """
        template = f"""主题: 【复试邀请】{position}岗位二面 - {candidate_name}

{candidate_name}，您好！

恭喜您通过了{position}岗位的初试！我们诚邀您参加复试。

【复试信息】
━━━━━━━━━━━━━━━━━━━━
• 岗位：{position}
• 时间：{interview_time}
• 面试官：{interviewer_name}（{interviewer_title}）
• 面试时长：约60分钟
━━━━━━━━━━━━━━━━━━━━

【面试形式】
{interview_focus if interview_focus else "本次面试将由部门负责人进行，重点考察您的专业能力和项目经验"}

【准备建议】
• 请准备1-2个代表您专业能力的项目案例
• 面试官可能会询问具体技术细节，请做好准备

请您确认是否参加复试，并回复本邮件。

期待您的精彩表现！

此致
敬礼

HR
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template
    
    @staticmethod
    def interview_reminder(
        candidate_name: str,
        position: str,
        interview_time: str,
        interview_location: str,
        interviewer_name: str,
        preparation_tips: str = ""
    ) -> str:
        """
        生成面试提醒邮件
        """
        template = f"""主题: 【面试提醒】{position}岗位面试明天进行 - {candidate_name}

{candidate_name}，您好！

温馨提醒：您的{position}岗位面试将在明天进行！

【面试信息】
━━━━━━━━━━━━━━━━━━━━
• 岗位：{position}
• 时间：{interview_time}
• 地点：{interview_location}
• 面试官：{interviewer_name}
━━━━━━━━━━━━━━━━━━━━

【面试温馨提示】
• 请提前5-10分钟到达
• 带上有效身份证件
• 如找不到地点可致电联系

{preparation_tips if preparation_tips else "祝您面试顺利！"}

如需调整时间或有其他问题，请尽快与我联系。

此致
敬礼

HR
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template


class EmailComposer:
    """邮件组合器 - 支持个性化参数"""
    
    def __init__(self):
        self.template = EmailTemplate()
    
    def compose(
        self,
        email_type: str,
        **kwargs
    ) -> str:
        """
        组合邮件
        
        Args:
            email_type: 邮件类型 (interview_invitation, rejection, offer, reminder)
            **kwargs: 邮件参数
        """
        composers = {
            'interview_invitation': self.template.interview_invitation,
            'rejection': self.template.rejection_email,
            'offer': self.template.offer_letter,
            'second_interview': self.template.second_interview_invitation,
            'reminder': self.template.interview_reminder,
        }
        
        composer = composers.get(email_type)
        if not composer:
            return f"[不支持的邮件类型: {email_type}]"
        
        return composer(**kwargs)


if __name__ == '__main__':
    composer = EmailComposer()
    
    print("=" * 50)
    print("邮件生成器测试")
    print("=" * 50)
    
    # 测试面试邀请
    print("\n[1] 面试邀请邮件:")
    print(composer.compose(
        'interview_invitation',
        candidate_name='张三',
        position='Python后端工程师',
        interview_time='2024年1月15日 14:00',
        interview_type='视频面试',
        interviewer_name='李经理'
    ))
    
    # 测试拒信
    print("\n[2] 拒绝邮件:")
    print(composer.compose(
        'rejection',
        candidate_name='李四',
        position='产品经理',
        feedback='我们认为您的经验与当前岗位的匹配度有限，祝您早日找到合适的岗位。'
    ))
    
    # 测试Offer
    print("\n[3] Offer Letter:")
    print(composer.compose(
        'offer',
        candidate_name='王五',
        position='前端工程师',
        department='研发部',
        entry_date='2024年2月1日',
        salary='25,000',
        probation_salary='20,000'
    ))
