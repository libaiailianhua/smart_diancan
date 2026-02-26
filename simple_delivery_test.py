#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单配送范围检查验证脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from tools.amap_tool import amap_tool
    
    print("开始测试配送范围检查功能...")
    
    # 测试基本功能
    user_address = "北京市海淀区中关村大街"
    restaurant_address = "北京市朝阳区三里屯"
    
    print(f"用户地址: {user_address}")
    print(f"餐厅地址: {restaurant_address}")
    print()
    
    # 测试所有配送模式
    print("1. 测试所有配送模式检查:")
    try:
        result = amap_tool.check_all_delivery_modes(user_address, restaurant_address)
        print(f"总体结果: {'在配送范围内' if result['all_in_range'] else '超出配送范围'}")
        print(f"汇总信息: {result['summary']}")
        print("详细结果:")
        for mode, mode_result in result['results'].items():
            print(f"  {mode}: {'✓' if mode_result['in_range'] else '✗'} {mode_result['message']}")
    except Exception as e:
        print(f"测试失败: {e}")
    
    print()
    
    # 测试单一模式
    print("2. 测试驾车配送模式:")
    try:
        result = amap_tool.check_delivery_range(user_address, restaurant_address, 'driving')
        print(f"结果: {'✓ 在配送范围内' if result['in_range'] else '✗ 超出配送范围'}")
        print(f"信息: {result['message']}")
        if result['actual_distance']:
            print(f"距离: {result['distance_text']}")
            print(f"时间: {result['duration_text']}")
    except Exception as e:
        print(f"测试失败: {e}")
        
except ImportError as e:
    print(f"导入错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")

print("\n验证完成")