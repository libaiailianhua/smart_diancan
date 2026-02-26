"""
高德地图工具模块

提供简单的地址解析、坐标转换、地理编码等功能
"""

import requests
import os
import logging
from typing import Dict, Any, Optional
import dotenv

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 加载环境变量
dotenv.load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobustSession:
    """带重试机制的HTTP会话类"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, timeout: int = 10):
        """
        初始化带重试机制的会话
        
        Args:
            max_retries (int): 最大重试次数
            retry_delay (float): 重试间隔时间（秒）
            timeout (int): 请求超时时间（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # 创建requests会话
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # 创建适配器并挂载到会话
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def get(self, url: str, **kwargs):
        """
        发送GET请求
        
        Args:
            url (str): 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            requests.Response: 响应对象，失败返回None
        """
        try:
            # 设置默认超时时间
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
                
            response = self.session.get(url, **kwargs)
            response.raise_for_status()  # 抛出HTTP错误
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return None
    
    def post(self, url: str, **kwargs):
        """
        发送POST请求
        
        Args:
            url (str): 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            requests.Response: 响应对象，失败返回None
        """
        try:
            # 设置默认超时时间
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
                
            response = self.session.post(url, **kwargs)
            response.raise_for_status()  # 抛出HTTP错误
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return None
    
    def close(self):
        """关闭会话"""
        if hasattr(self, 'session'):
            self.session.close()


class AmapTool:
    """高德地图API工具类"""
    
    # 配送范围配置（单位：米）
    DELIVERY_RANGES = {
        'driving': 5000,    # 驾车配送范围：5公里
        'walking': 2000,    # 步行配送范围：2公里
        'bicycling': 3000   # 骑行配送范围：3公里
    }
    
    def __init__(self):
        """初始化高德地图API配置"""
        self.api_key = os.getenv("AMAP_API_KEY")
        self.base_url = "https://restapi.amap.com/v3"
        # 创建带重试机制的会话
        self.session = RobustSession(max_retries=3, retry_delay=10.0, timeout=10)

        if not self.api_key:
            logger.warning("未找到高德地图API密钥，请在.env文件中设置AMAP_API_KEY")

    def __del__(self):
        """析构函数，确保会话被正确关闭"""
        if hasattr(self, 'session'):
            self.session.close()

    def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        地址转坐标（地理编码）
        
        Args:
            address (str): 地址字符串
            
        Returns:
            Optional[Dict]: 包含经纬度等信息的字典，失败返回None
        """
        if not self.api_key:
            logger.error("API密钥未配置")
            return None
            
        try:
            url = f"{self.base_url}/geocode/geo"
            params = {
                'address': address,
                'key': self.api_key,
                'output': 'json'
            }
            
            # 使用会话发送请求
            response = self.session.get(url, params=params)
            if not response:
                return None
                
            data = response.json()
            
            if data.get('status') == '1' and data.get('geocodes'):
                result = data['geocodes'][0]
                location = result['location'].split(',')
                return {
                    'longitude': float(location[0]),
                    'latitude': float(location[1]),
                    'formatted_address': result.get('formatted_address', address),
                    'province': result.get('province', ''),
                    'city': result.get('city', '')
                }
            else:
                logger.error(f"地址解析失败: {data.get('info', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"地址解析异常: {e}")
            return None

    def reverse_geocode(self, longitude: float, latitude: float) -> Optional[Dict[str, Any]]:
        """
        坐标转地址（逆地理编码）
        
        Args:
            longitude (float): 经度
            latitude (float): 纬度
            
        Returns:
            Optional[Dict]: 包含地址信息的字典，失败返回None
        """
        if not self.api_key:
            logger.error("API密钥未配置")
            return None
            
        try:
            url = f"{self.base_url}/geocode/regeo"
            params = {
                'location': f"{longitude},{latitude}",
                'key': self.api_key,
                'output': 'json'
            }
            
            # 使用会话发送请求
            response = self.session.get(url, params=params)
            if not response:
                return None
                
            data = response.json()
            
            if data.get('status') == '1' and data.get('regeocode'):
                result = data['regeocode']
                address_component = result.get('addressComponent', {})
                return {
                    'formatted_address': result.get('formatted_address', ''),
                    'province': address_component.get('province', ''),
                    'city': address_component.get('city', ''),
                    'district': address_component.get('district', ''),
                    'township': address_component.get('township', '')
                }
            else:
                logger.error(f"逆地理编码失败: {data.get('info', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"逆地理编码异常: {e}")
            return None

    def _request_route(self, api_type: str, origin: str, destination: str, 
                      extra_params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        通用路径规划请求方法
        
        Args:
            api_type (str): API类型 ('driving', 'walking', 'bicycling')
            origin (str): 起点坐标，格式："经度,纬度"
            destination (str): 终点坐标，格式："经度,纬度"
            extra_params (dict, optional): 额外参数
            
        Returns:
            Optional[Dict]: 路径规划结果，失败返回None
        """
        if not self.api_key:
            logger.error("API密钥未配置")
            return None
            
        try:
            # 构建URL
            if api_type == 'bicycling':
                url = "https://restapi.amap.com/v5/direction/bicycling"
            else:
                url = f"{self.base_url}/direction/{api_type}"
            
            # 构建基础参数
            params = {
                'origin': origin,
                'destination': destination,
                'key': self.api_key,
                'output': 'json'
            }
            
            # 添加额外参数
            if extra_params:
                params.update(extra_params)
            
            # 使用会话发送请求
            response = self.session.get(url, params=params)
            if not response:
                return None
                
            data = response.json()
            
            if data.get('status') == '1' and data.get('route'):
                route = data['route']
                paths = route.get('paths', [])
                
                if paths:
                    return self._parse_route_response(paths, api_type)
                else:
                    logger.error("未找到可行路径")
                    return None
            else:
                logger.error(f"{api_type}路径规划失败: {data.get('info', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"{api_type}路径规划异常: {e}")
            return None

    def _parse_route_response(self, paths: list, api_type: str) -> Dict[str, Any]:
        """
        解析路径规划响应
        
        Args:
            paths (list): 路径列表
            api_type (str): API类型
            
        Returns:
            Dict: 解析后的路径信息
        """
        # 解析第一条路径信息
        first_path = paths[0]
        
        # 计算总距离和时间
        total_distance = int(first_path.get('distance', 0))
        if api_type == 'bicycling':
            total_duration = int(first_path.get('duration', 0))
        else:
            total_duration = int(first_path.get('duration', 0))
        
        # 格式化距离文本
        if total_distance >= 1000:
            distance_text = f"{total_distance/1000:.1f}公里"
        else:
            distance_text = f"{total_distance}米"
            
        # 格式化时间文本
        if api_type == 'driving':
            duration_text = f"{total_duration//3600}小时{(total_duration%3600)//60}分钟"
        else:
            duration_text = f"{total_duration//60}分钟{(total_duration%60)}秒"
        
        return {
            'status': 'success',
            'total_distance': total_distance,  # 米
            'total_duration': total_duration,  # 秒
            'distance_text': distance_text,
            'duration_text': duration_text
        }

    def driving_route(self, origin: str, destination: str, 

                     strategy: int = 0) -> Optional[Dict[str, Any]]:
        """
        驾车路径规划
        
        Args:
            origin (str): 起点坐标，格式："经度,纬度"
            destination (str): 终点坐标，格式："经度,纬度"

            strategy (int): 路径计算策略
                0：速度优先（时间短）
                1：费用优先（不走收费路段）
                2：距离优先（路程短）
                3：不走高速
                4：躲避拥堵
                5：多策略（同时计算多条路线）
                6：不走高速且避免收费
                7：不走高速且躲避拥堵
                8：躲避收费和拥堵
                9：不走高速且躲避收费和拥堵
                
        Returns:
            Optional[Dict]: 路径规划结果，失败返回None
        """
        extra_params = {'strategy': strategy}
        return self._request_route('driving', origin, destination, extra_params)

    def walking_route(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """
        步行路径规划
        
        Args:
            origin (str): 起点坐标，格式："经度,纬度"
            destination (str): 终点坐标，格式："经度,纬度"
            
        Returns:
            Optional[Dict]: 路径规划结果，失败返回None
        """
        return self._request_route('walking', origin, destination)

    def bicycling_route(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """
        骑行路径规划
        
        Args:
            origin (str): 起点坐标，格式："经度,纬度"
            destination (str): 终点坐标，格式："经度,纬度"
            
        Returns:
            Optional[Dict]: 路径规划结果，失败返回None
        """
        extra_params = {'show_fields': 'cost'}
        return self._request_route('bicycling', origin, destination, extra_params)

    def check_delivery_range(self, user_address: str,
                           mode: str = 'driving') -> Dict[str, Any]:
        """
        检查用户地址是否在配送范围内
        
        Args:
            user_address (str): 用户输入的地址
            mode (str): 配送方式 ('driving', 'walking', 'bicycling')
            
        Returns:
            Dict: 配送范围检查结果，格式符合前端要求
        """
        try:
            # 获取配送范围限制
            max_distance = self.DELIVERY_RANGES.get(mode, 3000)  # 默认3公里
            
            # 获取路径规划结果

            restaurant_address = os.environ.get('RESTAURANT_ADDRESS')
            route_result = self.get_route_summary(restaurant_address, user_address, mode)
            
            if not route_result:
                return {
                    'success': False,
                    'in_range': False,
                    'distance': 0.0,
                    'formatted_address': '',
                    'duration': 0.0,
                    'message': f'{mode}模式下无法规划路径',
                    'travel_mode': self._convert_mode_to_number(mode),
                    'input_address': user_address
                }
            
            actual_distance = route_result['total_distance']
            distance_km = actual_distance / 1000.0  # 转换为公里
            duration_seconds = route_result['total_duration']  # 秒
            
            # 判断是否在配送范围内
            in_range = actual_distance <= max_distance
            
            if in_range:
                message = f'{self._convert_mode_to_chinese(mode)}模式下配送可达，距离{route_result["distance_text"]}，预计耗时{route_result["duration_text"]}'
            else:
                max_distance_text = f"{max_distance/1000:.1f}公里" if max_distance >= 1000 else f"{max_distance}米"
                message = f'{self._convert_mode_to_chinese(mode)}模式下超出配送范围，实际距离{route_result["distance_text"]}，最大配送距离{max_distance_text}'
            
            return {
                'success': True,
                'in_range': in_range,
                'distance': distance_km,
                'formatted_address': route_result.get('destination_address', user_address),
                'duration': duration_seconds,
                'message': message,
                'travel_mode': self._convert_mode_to_number(mode),
                'input_address': user_address
            }
            
        except Exception as e:
            logger.error(f"配送范围检查异常: {e}")
            return {
                'success': False,
                'in_range': False,
                'distance': 0.0,
                'formatted_address': '',
                'duration': 0.0,
                'message': f'配送范围检查失败: {str(e)}',
                'travel_mode': self._convert_mode_to_number(mode),
                'input_address': user_address
            }
    
    def _convert_mode_to_number(self, mode: str) -> str:
        """
        将配送模式转换为数字字符串
        
        Args:
            mode (str): 配送模式 ('driving', 'walking', 'bicycling')
            
        Returns:
            str: 对应的数字字符串 ('1', '2', '3')
        """
        mode_mapping = {
            'walking': '1',
            'bicycling': '2',
            'driving': '3'
        }
        return mode_mapping.get(mode, '3')
    
    def _convert_mode_to_chinese(self, mode: str) -> str:
        """
        将配送模式转换为中文描述
        
        Args:
            mode (str): 配送模式 ('driving', 'walking', 'bicycling')
            
        Returns:
            str: 对应的中文描述
        """
        mode_mapping = {
            'walking': '步行',
            'bicycling': '骑自行车',
            'driving': '驾车'
        }
        return mode_mapping.get(mode, '未知')

    def get_route_summary(self, origin_addr: str, dest_addr: str, 
                         mode: str = 'driving') -> Optional[Dict[str, Any]]:
        """
        获取路径规划摘要信息（根据地址自动获取坐标并规划路径）
        
        Args:
            origin_addr (str): 起点地址
            dest_addr (str): 终点地址
            mode (str): 出行方式 ('driving', 'walking', 'bicycling')
            
        Returns:
            Optional[Dict]: 路径规划摘要，失败返回None
        """
        # 先获取起点和终点坐标
        origin_coords = self.geocode(origin_addr)
        dest_coords = self.geocode(dest_addr)
        
        if not origin_coords or not dest_coords:
            logger.error("无法获取起点或终点坐标")
            return None
            
        origin_point = f"{origin_coords['longitude']},{origin_coords['latitude']}"
        dest_point = f"{dest_coords['longitude']},{dest_coords['latitude']}"
        
        # 根据出行方式调用相应的方法
        if mode == 'driving':
            route_result = self.driving_route(origin_point, dest_point)
        elif mode == 'walking':
            route_result = self.walking_route(origin_point, dest_point)
        elif mode == 'bicycling':
            route_result = self.bicycling_route(origin_point, dest_point)
        else:
            logger.error(f"不支持的出行方式: {mode}")
            return None
            
        if route_result:
            return {
                'origin_address': origin_addr,
                'destination_address': dest_addr,
                'mode': mode,
                'total_distance': route_result['total_distance'],
                'total_duration': route_result['total_duration'],
                'distance_text': route_result['distance_text'],
                'duration_text': route_result['duration_text']
            }
        else:
            return None


# 创建全局实例
amap_tool = AmapTool()

# 便捷函数
def get_coordinates(address: str) -> Optional[Dict[str, Any]]:
    """便捷函数：地址转坐标"""
    return amap_tool.geocode(address)

def get_address(longitude: float, latitude: float) -> Optional[Dict[str, Any]]:
    """便捷函数：坐标转地址"""
    return amap_tool.reverse_geocode(longitude, latitude)
def in_range(user_address: str, mode: str = 'driving') -> Dict[str, Any]:
    """
    便捷函数：是否在范围内
    """
    return amap_tool.check_delivery_range(user_address, mode)
def plan_driving_route(origin: str, destination: str, 

                      strategy: int = 0) -> Optional[Dict[str, Any]]:
    """便捷函数：驾车路径规划"""
    return amap_tool.driving_route(origin, destination, strategy)

def plan_walking_route(origin: str, destination: str) -> Optional[Dict[str, Any]]:
    """便捷函数：步行路径规划"""
    return amap_tool.walking_route(origin, destination)

def plan_bicycling_route(origin: str, destination: str) -> Optional[Dict[str, Any]]:
    """便捷函数：骑行路径规划"""
    return amap_tool.bicycling_route(origin, destination)

def get_route_summary(origin_addr: str, dest_addr: str, 
                     mode: str = 'driving') -> Optional[Dict[str, Any]]:
    """便捷函数：获取路径规划摘要"""
    return amap_tool.get_route_summary(origin_addr, dest_addr, mode)

if __name__ == '__main__':
    # 测试代码
    res=  get_address(  116.352704, 40.103543)
    print(res)