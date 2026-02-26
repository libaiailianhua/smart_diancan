"""
智能点餐助手 服务类封装

封装三个核心功能：
- smart_chat: 调用 assistant.py 中的 chat_with_assistant 函数
- delivery_check: 调用 check_delivery_range 函数 获取配送范围展示
- get_menu: 调用 get_menu_items_list 函数 获取菜品区域数据的展示
"""
def get_menu():
    """获取菜品区域的数据展示"""
    from tools.db_tool import get_menu_items
    return get_menu_items()

def check_delivery(user_address: str, restaurant_address: str = "北京市朝阳区三里屯"):
    """检查配送范围"""
    from tools.amap_tool import amap_tool
    return amap_tool.check_all_delivery_modes(user_address, restaurant_address)
def chat_with_assistant(user_input: str):
    """智能对话"""
    from agent.assistant import chat_with_assistant
    return chat_with_assistant(user_input)