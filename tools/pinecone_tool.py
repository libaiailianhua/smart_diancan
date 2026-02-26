"""
Pinecone向量数据库工具模块

该模块提供Pinecone向量数据库的连接和操作功能，
用于存储和查询菜品信息的向量化数据，支持语义搜索
"""
import pinecone
import dashscope
from dashscope import TextEmbedding
import dotenv
import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import ServerlessSpec

# 加载环境变量
dotenv.load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PineconeVectorDB:
    """
    Pinecone向量数据库操作类

    该类封装了Pinecone向量数据库的基本操作，包括：
    - 初始化连接和索引
    - 文本向量化（使用DashScope）
    - 数据插入和更新
    - 相似性搜索
    """

    def __init__(self):
        """初始化向量数据库连接参数"""
        # 从环境变量获取配置
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.env = os.getenv("PINECONE_ENV", "us-east-1")
        self.index_name = "menu-items-index"
        self.dimension = 1536  # DashScope text-embedding-v4的维度
        self.metric = "cosine"

        # 初始化Pinecone客户端
        self.pc = None
        self.index = None

        # 初始化DashScope
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

    def initialize_connection(self) -> bool:
        """
        初始化Pinecone连接和索引

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 初始化Pinecone客户端
            self.pc = pinecone.Pinecone(api_key=self.api_key)

            # 2. 检查索引是否存在
            existing_indexes = self.pc.list_indexes().names()

            if self.index_name not in existing_indexes:
                logger.info(f"索引 {self.index_name} 不存在，正在创建...")
                # 创建新索引
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.env
                    )
                )
                logger.info(f"索引 {self.index_name} 创建成功")
            else:
                logger.info(f"索引 {self.index_name} 已存在")

            # 3. 获取索引对象
            self.index = self.pc.Index(self.index_name)
            logger.info("Pinecone向量数据库初始化成功")
            return True

        except Exception as e:
            logger.error(f"Pinecone向量数据库初始化失败: {e}")
            return False

    def _embedding_content(self, text: str) -> Optional[List[float]]:
        """
        使用DashScope将文本转换为向量

        Args:
            text (str): 要向量化的文本

        Returns:
            Optional[List[float]]: 文本的向量表示，失败时返回None
        """
        try:
            # 调用DashScope文本嵌入API
            response = TextEmbedding.call(
                model='text-embedding-v4',
                input=text,
                dimension=self.dimension
            )

            if response.status_code == 200:
                # 提取嵌入向量
                embedding = response.output['embeddings'][0]['embedding']
                logger.info(f"文本 '{text[:50]}...' 向量化成功")
                return embedding
            else:
                logger.error(f"文本向量化失败: {response.message}")
                return None

        except Exception as e:
            logger.error(f"调用DashScope文本嵌入API失败: {e}")
            return None

    def upsert_vectors(self, vectors_data: List[Dict[str, Any]]) -> bool:
        """
        批量插入或更新向量数据

        Args:
            vectors_data (List[Dict[str, Any]]): 向量数据列表，每个元素包含id, values, metadata

        Returns:
            bool: 操作是否成功
        """
        try:
            if not self.index and not self.initialize_connection():
                logger.error("索引未初始化")
                return False

            # 批量插入数据
            self.index.upsert(vectors=vectors_data)
            logger.info(f"成功插入 {len(vectors_data)} 条向量数据")
            return True

        except Exception as e:
            logger.error(f"批量插入向量数据失败: {e}")
            return False

    def clear_index(self) -> bool:
        """
        清空索引中的所有向量数据

        Returns:
            bool: 操作是否成功
        """
        try:
            if not self.index and not self.initialize_connection():
                logger.error("索引未初始化")
                return False

            # 删除所有向量数据
            self.index.delete(delete_all=True)
            logger.info("索引数据清空成功")
            return True

        except Exception as e:
            logger.error(f"清空索引数据失败: {e}")
            return False

    def search_similar(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        根据查询文本搜索相似的向量

        Args:
            query_text (str): 查询文本
            top_k (int): 返回最相似的K个结果

        Returns:
            List[Dict[str, Any]]: 相似结果列表，包含id, score, metadata
        """
        try:
            if not self.index and not self.initialize_connection():
                logger.error("索引未初始化")
                return []

            # 1. 将查询文本向量化
            query_vector = self._embedding_content(query_text)
            if not query_vector:
                logger.error("查询文本向量化失败")
                return []

            # 2. 执行相似性搜索
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )

            # 3. 处理返回结果
            similar_items = []
            for match in results.matches:
                item = {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                }
                similar_items.append(item)

            logger.info(f"找到 {len(similar_items)} 个相似结果")
            return similar_items

        except Exception as e:
            logger.error(f"相似性搜索失败: {e}")
            return []

    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        Returns:
            Dict[str, Any]: 索引统计信息
        """
        try:
            if not self.index and not self.initialize_connection():
                logger.error("索引未初始化")
                return {}

            stats = self.index.describe_index_stats()
            return {
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': stats.namespaces,
                'total_vector_count': stats.total_vector_count
            }

        except Exception as e:
            logger.error(f"获取索引统计信息失败: {e}")
            return {}

    def split_menu_items_data(self, menu_items_string: str, chunk_size: int = 500) -> List[str]:
        """
        切分get_all_menu_items返回的菜品数据字符串
        
        Args:
            menu_items_string (str): get_all_menu_items函数返回的菜品信息字符串
            chunk_size (int): 每个切片的最大字符数，默认500
        
        Returns:
            List[str]: 切分后的菜品信息字符串列表
        """
        try:
            if not menu_items_string or not isinstance(menu_items_string, str):
                logger.warning("输入的菜品数据为空或不是字符串类型")
                return []
            
            # 按换行符分割成单独的菜品条目
            menu_lines = menu_items_string.strip().split('\n')
            
            if not menu_lines or menu_lines == ['']:
                logger.info("菜品数据为空")
                return []
            
            chunks = []
            current_chunk = []
            current_length = 0
            
            for line in menu_lines:
                line_length = len(line.encode('utf-8'))  # 计算字节长度更准确
                
                # 如果当前行加入后超过chunk_size，或者当前chunk已经有足够多的行
                if (current_length + line_length > chunk_size and current_chunk) or len(current_chunk) >= 10:
                    # 保存当前chunk
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = []
                        current_length = 0
                
                # 添加当前行到chunk
                current_chunk.append(line)
                current_length += line_length
            
            # 添加最后一个chunk
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            
            logger.info(f"菜品数据切分完成，共切分为 {len(chunks)} 个片段")
            return chunks
            
        except Exception as e:
            logger.error(f"切分菜品数据时发生错误: {e}")
            return []

    def process_and_vectorize_menu_items(self, chunk_size: int = 500) -> bool:
        """
        处理并向量化get_all_menu_items返回的菜品数据
        
        Args:
            chunk_size (int): 每个切片的最大字符数
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 1. 切分数据
            from db_tool import get_all_menu_items
            menu_items_string = get_all_menu_items()
            chunks = self.split_menu_items_data(menu_items_string, chunk_size)
            
            if not chunks:
                logger.warning("没有有效的菜品数据需要处理")
                return False
            
            # 2. 清空现有索引
            if not self.clear_index():
                logger.error("清空索引失败")
                return False
            
            # 3. 向量化并插入数据
            vectors_data = []
            for i, chunk in enumerate(chunks):
                # 向量化每个chunk
                vector = self._embedding_content(chunk)
                if vector:
                    vectors_data.append({
                        "id": f"menu_chunk_{i}",
                        "values": vector,
                        "metadata": {
                            "text": chunk,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    })
                    logger.info(f"成功向量化第 {i+1}/{len(chunks)} 个菜品数据片段")
                else:
                    logger.warning(f"第 {i+1}/{len(chunks)} 个菜品数据片段向量化失败")
            
            # 4. 批量插入向量数据
            if vectors_data:
                success = self.upsert_vectors(vectors_data)
                if success:
                    logger.info(f"成功处理并插入 {len(vectors_data)} 个菜品数据向量")
                    return True
                else:
                    logger.error("批量插入向量数据失败")
                    return False
            else:
                logger.warning("没有成功向量化的数据")
                return False
                
        except Exception as e:
            logger.error(f"处理和向量化菜品数据时发生错误: {e}")
            return False


# 全局实例
pinecone_db = PineconeVectorDB()


def embed_text(text: str) -> Optional[List[float]]:
    """
    全局文本向量化函数

    Args:
        text (str): 要向量化的文本

    Returns:
        Optional[List[float]]: 文本的向量表示
    """
    return pinecone_db._embedding_content(text)


def search_similar_items(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    全局相似性搜索函数

    Args:
        query (str): 查询文本
        top_k (int): 返回结果数量

    Returns:
        List[Dict[str, Any]]: 相似结果列表
    """
    return pinecone_db.search_similar(query, top_k)


def upsert_vector_data(vectors_data: List[Dict[str, Any]]) -> bool:
    """
    全局函数：快捷将向量数据存入向量数据库

    Args:
        vectors_data (List[Dict[str, Any]]): 向量数据列表，每个元素包含id, values, metadata

    Returns:
        bool: 操作是否成功

    Example:
        >>> vector_data = [{
        ...     "id": "item_1",
        ...     "values": [0.1, 0.2, 0.3, ...],  # 1536维向量
        ...     "metadata": {"text": "宫保鸡丁", "category": "川菜"}
        ... }]
        >>> upsert_vector_data(vector_data)
        True
    """
    return pinecone_db.upsert_vectors(vectors_data)


def format_search_results_for_frontend(query: str, top_k: int = 2) -> Dict[str, Any]:
    """
    根据问题进行相似性搜索并将结果格式化为字典格式,之后返回给前端

    Args:
        query (str): 搜索问题
        top_k (int): 返回结果数量，默认2个

    Returns:
        Dict[str, Any]: 格式化的搜索结果字典
            {
                'contents': List[str],      # 菜品文本内容列表
                'ids': List[int],           # 菜品ID数字列表
                'scores': List[float]       # 相似度得分列表
            }
    """
    try:
        # 执行相似性搜索
        search_results = search_similar_items(query, top_k)

        if not search_results or not isinstance(search_results, list):
            logger.warning("搜索结果为空或格式不正确")
            return {
                'contents': [],
                'ids': [],
                'scores': []
            }

        contents = []  # 存储菜品文本内容
        ids = []  # 存储菜品ID数字
        scores = []  # 存储相似度得分

        for result in search_results:
            # 提取文本内容
            metadata = result.get('metadata', {})
            text_content = metadata.get('text', '')
            if text_content:
                contents.append(text_content)
            else:
                contents.append('')  # 如果没有文本内容，添加空字符串

            # 提取ID数字 (从'menu_chunk_2'中提取数字2)
            item_id = result.get('id', '')
            if item_id and '_' in item_id:
                try:
                    id_number = int(item_id.split('_')[-1])
                    ids.append(id_number)
                except (ValueError, IndexError):
                    ids.append(0)  # 解析失败时默认为0
            else:
                ids.append(0)

            # 提取相似度得分
            score = result.get('score', 0.0)
            scores.append(float(score))

        result_dict = {
            'contents': contents,
            'ids': ids,
            'scores': scores
        }

        logger.info(f"搜索完成: 问题='{query}', 找到{len(contents)}个结果")
        return result_dict

    except Exception as e:
        logger.error(f"执行搜索和格式化时发生错误: {e}")
        return {
            'contents': [],
            'ids': [],
            'scores': []
        }
def get_vector_stats() -> Dict[str, Any]:
    """
    获取向量数据库统计信息

    Returns:
        Dict[str, Any]: 统计信息
    """
    return pinecone_db.get_index_stats()


if __name__ == "__main__":
    # import sys
    #
    # print("Pinecone向量数据库测试")
    # print("=" * 40)
    #
    # # 初始化数据库连接
    # if not pinecone_db.initialize_connection():
    #     print("✗ Pinecone数据库连接失败")
    #     sys.exit(1)
    #
    # print("✓ Pinecone数据库连接成功")
    #
    # # 获取初始统计信息
    # initial_stats = get_vector_stats()
    # print(f"初始索引统计: {initial_stats}")
    #
    # # 测试1: 文本向量化
    # print("\n测试1: 文本向量化功能")
    # test_text = "宫保鸡丁是一道经典的川菜"
    # vector = embed_text(test_text)
    # if vector and len(vector) == 1536:
    #     print(f"✓ 文本向量化成功，维度: {len(vector)}")
    # else:
    #     print("✗ 文本向量化失败")
    #
    # # 测试2: 向量插入
    # print("\n测试2: 向量插入功能")
    # if vector:
    #     vectors_data = [{"id": "test_1", "values": vector, "metadata": {"text": test_text}}]
    #     if pinecone_db.upsert_vectors(vectors_data):
    #         print("✓ 向量插入成功")
    #     else:
    #         print("✗ 向量插入失败")
    #
    # # 测试4: 完整的菜品数据处理流程
    # print("\n测试4: 完整菜品数据处理流程")
    # process_result = pinecone_db.process_and_vectorize_menu_items(chunk_size=300)
    # if process_result:
    #         print("✓ 菜品数据处理和向量化成功")
    #         # 验证结果
    #         final_stats = get_vector_stats()
    #         vector_count = final_stats.get('total_vector_count', 0)
    #         print(f"  当前索引向量总数: {vector_count}")
    # else:
    #         print("✗ 菜品数据处理失败")
    #
    # # 测试5: 相似性搜索
    # print("\n测试5: 相似性搜索功能")
    # search_queries = ["推荐川菜", "不辣的菜品", "素食选项"]
    #
    # for query in search_queries:
    #     results = search_similar_items(query, top_k=2)
    #     if results:
    #         print(f"  '{query}': 找到 {len(results)} 个结果")
    #         for result in results[:1]:  # 只显示第一个结果
    #             print(f"    - {result['id']}: 得分 {result['score']:.4f}")
    #     else:
    #         print(f"  '{query}': 未找到结果")
    #
    # print("\n" + "=" * 40)
    # print("测试完成")
    #
    # # 显示最终统计
    # final_stats = get_vector_stats()
    # print(f"最终索引统计: {final_stats}")
    # print("\n4.菜品的相似性检索,使用全局方法")
    #
    # similar_content=search_similar_items(query="请给我推荐素食系列的菜品",top_k=2)
    #
    # print(similar_content)
    similar_content=format_search_results_for_frontend("请给我推荐素食系列的菜品", 2)
    print(similar_content)

