"""
智能点餐助手 启动脚本

启动uvicorn web服务器
"""
import logging
logging.basicConfig(level=logging.INFO)
logger =logging.getLogger(__name__)
import uvicorn
def main():
    """
    启动uvicorn服务器入口
    """
    try:
        uvicorn.run("api.main:app",host="127.0.0.1",port=8000)
        logger.info("启动uvicorn服务器成功")
    except Exception as e:
        logger.info(f"启动uvicorn服务器失败异常为：{e}")
if __name__ == "__main__":
    main()#启动





