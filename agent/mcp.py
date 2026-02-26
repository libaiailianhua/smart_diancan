"""
实现LangChain中各个工具的定义（定义三个工具、工具一：实现常规问题的对话回答 工具二：实现菜品查询问题对话 工具三：实现距离范围配送问题对话）
"""
from tools.amap_tool import in_range
from tools.llm_tool import call_llm_api
from tools.pinecone_tool import search_similar_items, format_search_results_for_frontend

"""
实现LangChain中各个工具的定义（定义三个工具、工具一：实现常规问题的对话回答 工具二：实现菜品查询问题对话 工具三：实现距离范围配送问题对话）
"""

import os
from typing import Optional, Dict
from langchain_core.tools import tool, ToolException


def load_prompt(prompt_name: str) -> Optional[str]:
    """
    加载prompt目录下的提示词文件

    Args:
        prompt_name (str): 提示词文件名（不包含扩展名）

    Returns:
        Optional[str]: 提示词内容，如果文件不存在则返回None

    Example:
        >>> prompt = load_prompt("general_inquiry")
        >>> if prompt:
        ...     print("加载成功:", len(prompt), "字符")
    """
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_dir = os.path.join(project_root, "prompt")

    # 构造文件路径
    prompt_file = os.path.join(prompt_dir, f"{prompt_name}.txt")

    # 检查文件是否存在
    if not os.path.exists(prompt_file):
        print(f"提示词文件不存在: {prompt_file}")
        return None

    try:
        # 读取文件内容
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"读取提示词文件失败: {e}")
        return None
@tool
def general_inquiry(query: str, context: str=None) -> str:
    """
        常规问询工具

        处理用户的一般性问题，包括但不限于：
        - 餐厅介绍和服务信息
        - 营业时间和联系方式
        - 优惠活动和会员服务
        - 其他非菜品相关的咨询

        Args:
            query: 用户的问询内容
            context: 可选的上下文信息，用于提供更精准的回复

        Returns:
            str: 针对用户问询的智能回复

        Raises:
            ToolException: 当处理查询时发生错误
        """
    prompt = load_prompt("general_inquiry")
    full_query=f"当前提供的上下文:{context} \n\n 用户问题: {query}"if context else f"用户问题: {query}"
    return call_llm_api(full_query,prompt)
@tool
def dish_query(query: str) -> str:
    """
    智能菜品咨询工具

    专门处理与菜品相关的所有查询，包括：
    - 菜品介绍和详细信息
    - 价格和营养信息
    - 菜品推荐和搭配建议
    - 过敏原和饮食限制相关问题
    - 菜品可用性和特色介绍

    该工具会自动通过语义搜索找到最相关的菜品信息，然后基于这些信息回答用户问题。

    Args:
        query: 用户关于菜品的具体问题

    Returns:
        Dict[str, Any]: 包含推荐建议和菜品ID的字典
        {
            "recommendation": "基于菜品信息的推荐建议",
            "menu_ids": ["菜品ID1", "菜品ID2"]
        }

    Raises:
        ToolException: 当处理菜品查询时发生错误
    """

    prompt = load_prompt("menu_inquiry")
    similar_result = format_search_results_for_frontend(query, 2)
    # 3.构建菜品的查询
    if similar_result["contents"]:
        menu_context = "\n".join([f"- {content}" for content in similar_result["contents"]])
        full_query = f"用户问题:{query}\n\n 当前提供的菜品信息：\n{menu_context}\n\n请基于以上菜品信息回答用户的问题."
    else:
        full_query = f"用户问题：{query}\n\n抱歉，没有找到相关的菜品信息,请基于一般菜谱回答用户问题."

    res =call_llm_api(full_query,prompt)
    return res


@tool
def delivery_check_tool(address: str, travel_mode: str) -> str:
    """
    配送范围检查工具

    检查指定地址是否在配送范围内，并提供距离信息。

    Args:
        address: 配送地址
        travel_mode: 距离计算方式 (1=步行距离, 2=骑行距离, 3=驾车距离)

    Returns:
        str: 配送检查结果的格式化信息

    Raises:
        ToolException: 当配送检查失败时
    """

    # 调用配送检查功能
    try:
        MODE_MAPPING = {
            "1": "walking",
            "2": "bicycling",
            "3": "driving"
        }
        result = in_range(address,MODE_MAPPING.get(travel_mode))
        if result["success"]:
            status_text = "✅ 可以配送" if result["in_range"] else "❌ 超出配送范围"

            response = f"""
        配送信息查询结果：
        配送地址：{result['formatted_address']}， 配送距离：{result['distance']}公里 ({MODE_MAPPING[travel_mode]})
        配送状态：{status_text}
                    """.strip()

        else:
            response = f"❌ 配送查询失败：{result['message']}"

        return response
    except  Exception as e:
        raise ToolException(f"配送检查失败: {str(e)}")
if __name__ == "__main__":
    print("\n1.常规问题工具的测试")

    # 1.1 参数用字符串(工具参数只有一个)
    # general_inquiry_result=general_inquiry.invoke(input="请问您们餐厅的营业时间是什么时候?")
    # 1.2 参数用字符串(工具参数只有一个)
    # general_inquiry_result=general_inquiry.invoke("请问您们餐厅的营业时间是什么时候?")
    # 1.3 参数用字典(工具参数只有一个)
    general_inquiry_result = general_inquiry.invoke({"query": "请问您们餐厅的营业时间是什么时候"})

    print(f"常规问题工具的结果:{general_inquiry_result}")  # str

    print("\n2.菜品推荐问题工具的测试")

    # menu_inquiry_result = menu_inquiry.invoke({"query":"请给我推荐一些素食的菜品"})
    menu_inquiry_result = dish_query.invoke({"query": "请给我推荐蒜蓉西兰花菜品"})
    print(f"菜品推荐问题工具的结果:{menu_inquiry_result}")  # dict
    # 菜品推荐问题工具的结果:
    # {
    #   'recommendation': '您好！根据您的需求，我为您推荐以下两款美味的素食菜品：\n\n1. 清炒时蔬（¥15.00）\n这款菜品选用当季新鲜时令蔬菜，搭配蒜蓉清炒而成。它的特点在于保留了蔬菜本身的鲜嫩口感，清淡爽口，非常适合追求健康饮食的人群。清炒的方式最大限度地锁住了蔬菜中的营养成分，让您既能享受美味又能保持身材。而且它没有任何过敏原，您可以放心食用。\n\n2. 蒜蓉西兰花（¥12.00）\n这道菜采用新鲜的西兰花为主料，配以蒜蓉蒸炒而成。西兰花富含维生素C、胡萝卜素等营养成分，对身体非常有益。这道菜口感清新，带有浓郁的蒜香，既保留了西兰花的脆嫩又不失其原汁原味。同样，这道菜也是素食，且没有过敏原，非常适合您选择。\n\n如果您想要更加清淡健康的菜肴，我会更倾向于推荐清炒时蔬；如果您喜欢浓郁的蒜香味，则可以尝试蒜蓉西兰花。这两款菜品都是素食，且均不含过敏原，您可以根据自己的口味喜好进行选择。希望我的推荐能够帮助到您！',
    #   'menu_ids': ['3', '5'] # 向量数据库id
    # }
    # 菜品推荐问题工具的结果:
    # {
    #   'recommendation': '您好！很高兴为您推荐蒜蓉西兰花这道美味又健康的菜品。\n\n**蒜蓉西兰花**\n- **价格**: ¥12.00\n- **特色**: 这道菜选用新鲜的西兰花，搭配蒜蓉调味，简单却充满浓郁的蒜香。采用蒸炒的烹饪方式，最大程度地保留了西兰花的营养成分，口感鲜嫩脆爽。\n- **营养亮点**: 西兰花富含维生素C、膳食纤维以及多种抗氧化物质，非常适合作为减肥期间的健康选择。\n- **特别之处**: 不仅味道鲜美，而且完全不含任何过敏原，是一款非常安全的素食选择。\n- **搭配建议**: 可以作为主菜搭配米饭或面条一起食用；也可以与豆腐、鸡蛋等其他食材搭配，增加菜肴的层次感。\n- **性价比**: 价格实惠，每份仅需12元，让您以亲民的价格享受高品质的健康美食。\n\n如果您对这道菜感兴趣的话，可以放心点餐，相信它一定会给您带来美妙的味觉体验！如果您还有其他特殊需求或者想要了解更多信息，我很乐意为您提供帮助。',
    #   'menu_ids': ['5', '3']   # 向量数据库id
    #  }