
"""
智能点餐助手主程序 FastAPI 接口
1.定义FastAPI应用实例
2.提供三个主要接口：
2.1 POST /chat - 智能对话接口
2.2 POST /delivery - 配送查询接口
2.3 GET /menu/list - 菜品列表接口
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app=FastAPI(title="智能点餐助手", description="智能点餐应用主要暴露三个接口分别为智能对话接口、配送查询接口、菜品列表接口")

@app.get("/")
def hello_world():
 return {"hello":"world"}

@app.get("/healthy")
def healthy():
    return {"message":"测试请求路径/healthy访问正常"}

#定义数据模型
#菜品列表展示
class MenuListResponse(BaseModel):
    """菜品列表响应"""
    success:bool
    menu_items:List[dict] # 菜品列表
    count:int #菜品数
    message:str #响应消息提示


@app.get("/menu/list",response_model=MenuListResponse)
async def menu_list_endpoint():
    """菜品列表区域展示"""
    #1.引用service
    from service.diancan_service import get_menu
    #2，调用方法
    menu_items=get_menu()
    #3.封装结果并返回
    if not menu_items:
        return MenuListResponse(
            success=False,
            menu_items=[],
            count=0,
            message="暂无菜品列表可用"
        )
    return MenuListResponse(
        success=True,
        menu_items=menu_items,
        count=len(menu_items),
        message=f"成功查询到{len(menu_items)}道菜品"
    )
# 配送查询数据模型
# 定义配送范围查询的请求模型
class DeliveryRequest(BaseModel):
    """配送范围查询请求"""
    address: str
    travel_mode: str = "2"  # 1=步行, 2=骑自行车, 3=驾车

class DeliveryResponse(BaseModel):
    """配送查询响应"""
    success: bool  # 成功(True) or 失败的标识（False）
    in_range: bool #  配送是否在配送范围内(True False)
    distance: float # 配送距离(公里 km)
    formatted_address: str # 格式化地址
    duration:float # 配送时间（秒）
    message: str  # (前端要展示的配送完整消息内容)
    travel_mode: str # 配送模式 (1:步行 2:骑自行车 3:驾车)
    input_address: str # 输入原始内容

# 配送查询接口
@app.post("/delivery", response_model=DeliveryResponse)
async def delivery_check(request: DeliveryRequest):
    """配送范围检查接口
    
    根据用户地址和配送方式检查是否在配送范围内
    """
    mode_mapping = {
        "1": "walking",
        "2": "bicycling",
        "3": "driving"
    }
    try:
        # 引入配送工具
        from tools.amap_tool import amap_tool
        
        # 调用配送范围检查
        result = amap_tool.check_delivery_range(
            user_address=request.address,
            mode=mode_mapping.get(request.travel_mode)
        )

        # 封装响应结果
        return DeliveryResponse(
            success=True,
            in_range=result['in_range'],
            distance=result.get('actual_distance', 0.0),
            formatted_address=result.get('formatted_address', ''),
            duration=result.get('duration', 0.0),
            message=result['message'],
            travel_mode=mode_mapping.get(request.travel_mode),
            input_address=request.address
        )

    except Exception as e:
        # 处理异常情况
        return DeliveryResponse(
            success=False,
            in_range=False,
            distance=0.0,
            formatted_address='',
            duration=0.0,
            message=f"配送范围检查失败: {str(e)}",
            travel_mode=mode_mapping.get(request.travel_mode),
            input_address=request.address
        )
# 智能对话数据模型
class ChatRequest(BaseModel):
    """智能对话请求"""
    query: str

class ChatResponse(BaseModel):
    """智能对话响应"""
    success: bool # 成功失败表示
    query: str # 原始查询内容
    response: Optional[str] = None # 响应内容
    recommendation: Optional[str] = None # 推荐内容
    menu_ids: Optional[List[str]] = None # 推荐的菜品id

# 智能对话接口
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """智能对话接口
    
    根据用户查询内容进行智能对话，返回相关推荐和菜品信息
    """
    try:
        # 引入智能对话服务
        from service.diancan_service import chat_with_assistant
        
        # 调用智能对话功能
        result = chat_with_assistant(request.query)
        # 封装响应结果
        return ChatResponse(
            success=True,
            query=request.query,
            response=result
        )
        
    except Exception as e:
        # 处理异常情况
        logger.error(f"智能对话处理失败: {str(e)}")
        return ChatResponse(
            success=False,
            query=request.query,
            response=f"对话处理失败: {str(e)}",
            recommendation=None,
            menu_ids=[]
        )

