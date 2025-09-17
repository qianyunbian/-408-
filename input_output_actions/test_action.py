#!/usr/bin/env python3
"""
测试动作脚本
这个文件用于测试脚本编辑功能
"""

def process(input_text, input_source, output_target):
    """
    测试处理函数
    
    Args:
        input_text (str): 输入的文本内容
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 处理后的结果文本
    """
    
    # 简单的测试处理
    if input_text:
        result = f"测试处理结果:\n"
        result += f"输入内容: {input_text}\n"
        result += f"输入源: {input_source}\n"
        result += f"输出目标: {output_target}\n"
        result += f"处理时间: {__import__('datetime').datetime.now()}\n"
        return result
    else:
        return "没有输入内容"