"""
HR Skill MCP Server
将 hr_tools.py 中的工具封装为 MCP 服务,供 AI 工具调用
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("hr-skill")


def _warmup():
    """启动预热：提前导入重量级库，避免首次工具调用时冷启动超时"""
    # 预热 PDF 处理库
    try:
        import fitz
    except ImportError:
        pass

    # 预热 OCR 库并探测 tesseract 路径
    try:
        import pytesseract
        from scripts.hr_tools import _auto_detect_tesseract
        _auto_detect_tesseract()
    except ImportError:
        pass

    # 预热 Word 文档库
    try:
        from docx import Document
    except ImportError:
        pass

    # 预热 PIL
    try:
        from PIL import Image
    except ImportError:
        pass


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="load_resume_file",
            description="读取 PDF/Word/图片简历，返回纯文本（图片型 PDF 自动 OCR）",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "简历文件路径"}},
                "required": ["file_path"]
            }
        ),
        Tool(
            name="load_candidate_batch",
            description="批量加载文件夹内所有简历",
            inputSchema={
                "type": "object",
                "properties": {"folder_path": {"type": "string", "description": "文件夹路径"}},
                "required": ["folder_path"]
            }
        ),
        Tool(
            name="get_evaluation_guide",
            description="返回 HR 评估框架：评分维度、A/B/C 分层标准、STAR 面试问题模板",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_risk_checklist",
            description="返回简历风险信号清单（含语境豁免说明）",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_skill_alias_map",
            description="技能别名映射表（js→JavaScript, k8s→Kubernetes 等）",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="market_salary_query",
            description="查询指定岗位在指定城市的市场薪资参考范围",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {"type": "string", "description": "岗位名称"},
                    "city": {"type": "string", "description": "城市"},
                    "experience_years": {"type": "integer", "description": "工作年限"}
                },
                "required": ["position", "city"]
            }
        ),
        Tool(
            name="get_compare_prompt",
            description="返回候选人横向对比框架模板",
            inputSchema={
                "type": "object",
                "properties": {
                    "candidate_count": {"type": "integer", "description": "候选人数量", "default": 2}
                },
                "required": []
            }
        ),
        Tool(
            name="get_report_prompt",
            description="返回给用人经理的决策报告段落框架",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    from scripts.hr_tools import (
        load_resume_file,
        load_candidate_batch,
        get_evaluation_guide,
        get_risk_checklist,
        get_skill_alias_map,
        market_salary_query,
        get_compare_prompt,
        get_report_prompt,
    )
    import anyio

    try:
        if name == "load_resume_file":
            result = await anyio.to_thread.run_sync(load_resume_file, arguments["file_path"])
        elif name == "load_candidate_batch":
            result = await anyio.to_thread.run_sync(load_candidate_batch, arguments["folder_path"])
        elif name == "get_evaluation_guide":
            result = get_evaluation_guide()
        elif name == "get_risk_checklist":
            result = get_risk_checklist()
        elif name == "get_skill_alias_map":
            result = get_skill_alias_map()
        elif name == "market_salary_query":
            result = market_salary_query(
                arguments["position"],
                arguments["city"],
                arguments.get("experience_years", 0)
            )
        elif name == "get_compare_prompt":
            result = get_compare_prompt(arguments.get("candidate_count", 2))
        elif name == "get_report_prompt":
            result = get_report_prompt()
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

        if isinstance(result, (dict, list)):
            text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            text = str(result)
        return [TextContent(type="text", text=text)]

    except Exception as e:
        return [TextContent(type="text", text=f"错误: {e}")]


async def main():
    _warmup()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
