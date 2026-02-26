"""
智能点餐助手主程序

该程序构建了一个包含工具选择功能的LLM系统(相当于LangChain中的Agent角色)，能够：
1. 自动选择合适的工具（常规咨询、菜品推荐、配送范围检查）
2. 调用相应工具并返回结果
3. 提供自然、友好的对话体验
"""

import json
import logging
import time
from json import JSONDecodeError

from dotenv import load_dotenv
from typing import Dict, Optional
from tools.llm_tool import call_llm_api
from agent.mcp import general_inquiry, dish_query, delivery_check_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


class SmartRestaurantAssistant:
    """智慧点餐小助手类"""

    def __init__(self):
        """构造函数 初始化小助手需要的参数"""

        self.tools = {
            "general_inquiry": general_inquiry,  # 一般性问题的对话
            "menu_inquiry": dish_query,  # 菜品检索问题的对话
            "delivery_check_tool": delivery_check_tool  # 配送范围查询的对话
        }

        # 意图分析系统指令
        self.intent_instruction = """你是一个智能餐厅助手的意图分析器。
        请分析用户问题意图，并且选择最合适的工具来处理：

        工具说明：
        1. general_inquiry: 处理餐厅常规咨询（营业时间、地址、电话、优惠活动、预约等）
        2. menu_inquiry: 处理智能菜品推荐和咨询（推荐菜品、介绍菜品、询问菜品信息、点餐等）
        3. delivery_check_tool: 处理配送范围检查（查询某个地址是否在配送范围内、能否送达等）

        你必须严格按照以下JSON格式返回，不要包含任何其他文字：
        {{
            "tool_name": "工具名称",
             "format_query": "处理后的用户问题"
        }}

        正确示例：
        用户："你们几点营业？" -> {{"tool_name": "general_inquiry", "format_query": "营业时间"}}
        用户："推荐川菜系列的菜品" -> {{"tool_name": "menu_inquiry", "format_query": "推荐川菜"}}
        用户："能送到武汉大学吗？" -> {{"tool_name": "delivery_check_tool", "format_query": "武汉大学"}}

        重要规则：
        - 只返回纯JSON，不要有任何额外字符和解释,字典内部不能有空格，与换行
        - 确保JSON格式完全正确
        - tool_name必须是以下之一：general_inquiry, menu_inquiry, delivery_check_tool
        - format_query要简洁明了地概括用户问题

        记住：如果你错误的选择工具，系统将会出现崩溃。"""

        self.max_retries = 3  # 重试次数3次
        self.retry_delay = 1  # 重试间隔1s

    def _fallback_intent_analysis(self, query: str) -> Dict[str, str]:
        """兜底意图分析"""
        logger.info("使用兜底意图分析")
        # 配送相关关键词
        delivery_keywords = ["配送", "送达", "送到", "送货", "外卖", "地址", "区域", "范围"]
        # 菜单相关关键词
        menu_keywords = ["菜单", "菜品", "推荐", "点餐", "招牌", "特色", "什么好吃", "有什么菜"]

        # 检查配送意图
        if any(keyword in query for keyword in delivery_keywords):

            return {"tool_name": "delivery_check_tool", "format_query": query}

        # 检查菜单意图
        elif any(keyword in query for keyword in menu_keywords):
            return {"tool_name": "menu_inquiry", "format_query": query}

        # 默认常规咨询
        else:
            return {"tool_name": "general_inquiry", "format_query": query}

    def _clean_json_response(self, response: str) -> str:
        """
        清理JSON响应，移除可能的markdown代码块标记等

        """
        # 1.移除 ```json 和 ``` 标记
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]

        # 2.移除首尾空白
        response = response.strip()

        # 3.如果响应以 { 开头但可能包含其他内容，尝试提取第一个完整的JSON对象
        start_idx = response.find('{')
        end_idx = response.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            response = response[start_idx:end_idx + 1]

        return response

    def _analyse_intent(self, query: str, last_error: str) -> Dict[str, str]:
        """分析自然语言语义 返回工具信息"""

        try:
            instruction = self.intent_instruction
            if last_error:
                instruction += f"\n\n上次解析失败，错误信息：{last_error}\n请根据错误信息修正JSON格式，确保返回正确的JSON。"

            llm_json_str_response = call_llm_api(query, instruction)
            logger.info(f"模型原始响应: {llm_json_str_response}")

            # 尝试清理响应，移除可能的markdown代码块标记
            cleaned_response = self._clean_json_response(llm_json_str_response)
            logger.info(f"清理后的响应: {cleaned_response}")
            structured_response = json.loads(cleaned_response)

            # 验证必需字段
            if not all(key in structured_response for key in ["tool_name", "format_query"]):
                raise JSONDecodeError("缺少必需字段", cleaned_response, 0)

            # 验证工具名称有效性
            if structured_response["tool_name"] not in self.tools:
                raise ValueError(f"无效的工具名称: {structured_response['tool_name']}")

            return structured_response

        except (JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON解析失败: {e}")
            raise e  # 将异常抛给上层处理重试

    def analyse_intent_with_retry(self, query: str) -> Dict[str, str]:
        logger.info(f"分析用户意图: {query}")

        last_error = None
        for retry in range(self.max_retries):
            try:
                result = self._analyse_intent(query, last_error)
                logger.info(f"意图分析成功: {result}")
                return result
            except(JSONDecodeError, ValueError) as e:
                last_error = str(e)
                logger.warning(f"第 {retry + 1} 次尝试失败: {last_error}")

                if retry < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"经过 {self.max_retries} 次重试后仍然失败，使用兜底方案")

        return self._fallback_intent_analysis(query)

    def execute_tool(self, format_query: str, selected_tool: str) ->Optional[Dict[str, str] or str]:
        """执行工具"""

        try:
            # 1.判断选择工具到底是哪个
            if selected_tool == "general_inquiry":  # 处理通用问题的工具
                general_inquiry_tool = self.tools[selected_tool]
                return general_inquiry_tool.invoke({"query": format_query, "context": ""})
            elif selected_tool == "menu_inquiry":  # 处理菜品相关问题的工具
                menu_inquiry_tool = self.tools[selected_tool]
                return menu_inquiry_tool.invoke({"query": format_query})
            else:
                delivery_check_tool = self.tools[selected_tool]
                return delivery_check_tool.invoke({"address": format_query, "travel_mode": "2"})  # 骑行(电动车)

        except Exception as e:
            logger.error(f"工具：{selected_tool}执行出错,原因：{str(e)}")
            return f"工具：{selected_tool}执行出错"

    def chat(self, user_query: str):
        """智慧点餐小助手的聊天入口(Agent角色【手写版Agent流程】)"""
        try:
            print(f"用户输入的问题:{user_query}...")

            # 1.对用户意图分析，找工具
            struct_response = self.analyse_intent_with_retry(user_query)
            selected_tool_name = struct_response['tool_name']
            format_query = struct_response['format_query']
            print(f"选择工具:{selected_tool_name}\n格式化后的问题:{format_query}")

            # 2.执行工具
            exec_tool_output = self.execute_tool(format_query, selected_tool_name)

            print(f"工具:{selected_tool_name}执行结束...")
            # 3.工具的结果返回
            return exec_tool_output

        except Exception as e:
            logger.error(f"执行业务出错{str(e)}")
            return f"执行业务出错{str(e)}"


# 全局方法 方便别的模块直接使用

def chat_with_assistant(query: str):
    """全局智能餐厅对话聊天入口"""

    try:
        # 1.处理query
        query = query or "请给我介绍一下您们餐厅的基本信息。"  # 默认查询内容

        # 2.实例化小助手
        smart_assistant = SmartRestaurantAssistant()

        # 3.调用小助手入口
        assistant_chat = smart_assistant.chat(query)

        # 4.打印小助手回复
        print(f"\n小助手的回复:\n{assistant_chat}")

        return assistant_chat

    except Exception as e:
        return f"智慧点餐助手执行失败{str(e)}"