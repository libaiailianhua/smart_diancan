"""
llm_tool模块
该模块提供了通用的llm调用
将llm调用进行封装,在后续调用时只需调用call_llm即可
"""

import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# 加载环境变量
load_dotenv()

def call_llm_api(human_message, system_message: str="你是一个智能助手帮助用户解决问题") :
    """
    创建LLM链，包含提示词和模型调用

    Returns:
        LLMChain: 构建好的链对象
    """
    # 获取模型配置
    api_key = os.getenv("DASHSCOPE_API_KEY")
    api_base = os.getenv("DASHSCOPE_API_BASE")
    default_model = os.getenv("LLM_MODE", "qwen2.5-14b-instruct")
    
    model_name = default_model
    
    # 初始化LLM
    llm = ChatOpenAI(
        model=model_name,
        base_url=api_base,
        api_key=api_key,
        temperature=0.7,
        max_tokens=2048
    )
    
    # 创建提示词模板
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system",f"{system_message}"),
        ("human", f"{human_message}")
    ])
    # 创建链
    chain = chat_prompt | llm| StrOutputParser()
    res= chain.invoke({"system_message":system_message, "human_message":human_message})
    return res

if __name__ == "__main__":
    # 测试代码
    system_message = "你是一个智能餐厅助手"
    human_message = "我想点一份牛皮，有什么推荐吗？"
    res= call_llm_api(human_message,system_message)
    # 正确的调用方
    print(res)

