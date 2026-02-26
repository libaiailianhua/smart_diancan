"""
数据库查询工具模块

该模块提供MySQL数据库连接和查询功能，
专门用于查询menu数据库中的menu_items表的全部信息
"""
from typing import Dict, List, Any
import dotenv
import os

from numpy.core.multiarray import item
from zmq import NULL

dotenv.load_dotenv()
import mysql.connector
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class DataBaseConnection:
    """
    数据库查询工具类
    """
#1.定义数据库配置信息
    def __init__(self):
      self.host = os.getenv("MYSQL_HOST", "localhost")
      self.port = int(os.getenv("MYSQL_PORT", "3306"))
      self.user = os.getenv("MYSQL_USER", "root")
      self.password = os.getenv("MYSQL_PASSWORD", "root")
      self.database = os.getenv("MYSQL_DATABASE", "db01")
      #初始化连接对象与游标对象
      self.connection = None
      self.cursor = None
    def initialize_connection(self)->bool:
      """
      初始化连接对象与游标对象
      """
      try:
        #初始化连接对象
        self.connection = mysql.connector.connect(
          host=self.host,
          port=self.port,
          user=self.user,
          password=self.password,
          database=self.database,
          charset="utf8",
        )
        self.cursor=self.connection.cursor(dictionary=True)#？字典什么含义
        logger.info(f"数据库{self.database}初始化连接成功")
        return True
      except mysql.connector.Error as e:
        logger.info(f"数据库{self.database}初始化连接失败:{e}")
        return False
    def disconnect_connection(self)->bool:
      try:
        #关闭游标对象
        if self.cursor:
          self.cursor.close()
          self.cursor=None
        #关闭连接对象
        if self.connection and self.connection.is_connected():
          self.connection.close()#断开外部连接
          self.connection=None#内部置空
        logger.info(f"数据库{self.database}游标对象与连接对象关闭成功")
        return True
      except mysql.connector.Error as e:
        logger.info(f"数据库{self.database}游标对象与连接对象关闭失败：{e}")
        return False
    #上下文管理器对象用来自动建立连接，与释放资源
    def __enter__(self):
      """
      上下文管理器对象enter的用法
      在with代码块执行之前调用，返回一个上下文管理器对象
      """
      if self.initialize_connection():
        logger.info("数据库初始化成功")
        return self
      else:
        raise Exception
    def __exit__(self, exc_type, exc_val, exc_tb):
      """
      上下文管理器对象exit的用法
      在with代码块执行之后调用，可查看异常类型
      """
      self.disconnect_connection()
      if exc_type:
        logger.info(f"执行with代码块出现异常:{exc_val}")
      return False


def get_all_menu_items() -> str:
    """
    作用：查询menu_items中所有的菜品信息，并且对每一条菜品信息用\n连接，最终形成一个大字符串（向量化）
    :return:str
    """

    try:
        with DataBaseConnection() as db:
            # 1.定义SQL语句
            query_sql = """
              SELECT
                    id, dish_name, price, description, category,
                    spice_level, flavor, main_ingredients, cooking_method,
                    is_vegetarian, allergens, is_available
                FROM menu_items
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            #2.执行sql并获取返回结果
            db.cursor.execute(query_sql)
            menu_items=db.cursor.fetchall()
            #3.处理结果并返回
            menu_item_list=[]
            for item in menu_items:
                #3.1格式化辣度等级
                spice_level_mapping={0:"不辣",1:"微辣",2:"中辣",3:"重辣"}
                spice_level=spice_level_mapping.get(item.get('spice_level',"暂无辣度信息"))
                #3.2格式化是否素食
                format_is_vegetarian="是" if item.get('is_vegetarian') else "否"
                #3.3格式化菜品描述
                description=item.get('description') if item.get('description').strip() else "暂无菜品描述"
                #3.4格式化主要食材
                main_ingredients = item.get('main_ingredients') if item.get('main_ingredients').strip() else "暂无主要食材"
                #3.5格式化过敏原
                allergens = item.get('allergens') if item.get('allergens').strip() else "暂无过敏源"
                #3.6拼接菜品结构为字符串
                menu_item_str=f"菜品名称：{item.get('dish_name')}，价格：{item.get('price')}，辣度：{spice_level}，是否素食：{format_is_vegetarian}，描述：{description}，主要食材：{main_ingredients}，过敏源：{allergens}"
                menu_item_list.append(menu_item_str)
            logger.info(f"查询菜品信息成功，且条数为{len(menu_item_list)}")
        return "\n".join(menu_item_list)
    except Exception as e:
        logger.info(f"查询数据库结构化信息失败异常为：{e}")
def get_menu_items() -> List[Dict[str, Any]]:
    """
    查询菜品信息，用于前端展示
    """
    try:
        with DataBaseConnection() as db:
            # 1.定义SQL语句
            query_sql = """
                        SELECT
                    id, dish_name, price, description, category,
                    spice_level, flavor, main_ingredients, cooking_method,
                    is_vegetarian, allergens, is_available
                FROM menu_items
                WHERE is_available = 1
                ORDER BY category, dish_name
            """
            # 2.执行sql并获取返回结果
            db.cursor.execute(query_sql)
            menu_items = db.cursor.fetchall()
            if not menu_items:
                logger.info("没有查询到菜品信息")
                return []
            menu_items_list = []
            for item in menu_items:
                # 3.处理结果并返回
                # 3.1格式化辣度等级
                spice_level_mapping = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}
                spice_text = spice_level_mapping.get(item.get('spice_level'), "暂无辣度信息")
                processed_item={
                    "id": item['id'],
                    "dish_name": item['dish_name'],
                    "price": float(item['price']),
                    "formatted_price": f"¥{item['price']:.2f}",
                    "description": item['description'] or "暂无描述",
                    "category": item['category'],
                    "spice_level": item['spice_level'],
                    "spice_text": spice_text,
                    "flavor": item['flavor'] or "暂无口味",
                    "main_ingredients": item['main_ingredients'] or "暂无主要食材",
                    "cooking_method": item['cooking_method'] or "暂无烹饪方法",
                    "is_vegetarian": bool(item['is_vegetarian']),
                    "vegetarian_text": "是" if item['is_vegetarian'] else "否",
                    "allergens": item['allergens'] if item['allergens'] and item['allergens'].strip() else "暂无过敏原",
                    "is_available": bool(item['is_available'])
                }
                menu_items_list.append(processed_item)
            logger.info(f"查询菜品信息成功，且条数为{len(menu_items_list)}")
            return menu_items_list
    except Exception as e:
        logger.info(f"查询数据库结构化信息失败异常为：{e}")
        return []

if __name__== "__main__":
    #测试数据库连接
    # with DataBaseConnection() as db:
        # 1.定义SQL语句
        # query_sql = """
        #       SELECT
        #             id, dish_name, price, description, category,
        #             spice_level, flavor, main_ingredients, cooking_method,
        #             is_vegetarian, allergens, is_available
        #         FROM menu_items
        #         WHERE is_available = 1
        #         ORDER BY category, dish_name
        #     """
        # # 2.执行sql并获取返回结果
        # db.cursor.execute(query_sql)
        # menu_items = db.cursor.fetchall()
        # print(menu_items)
    # 测试菜品信息
    #res= get_all_menu_items()
    # print(res)
    #测试前端菜品信息
    # res= get_menu_items()
    # for index, item in enumerate(res,1):
    #     print(f"{index}. {item['dish_name']}")
    pass



