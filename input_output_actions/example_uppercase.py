# 文本大写转换示例
# 将剪贴板或选中的文本转换为大写

def process(input_text, input_source, output_target):
    """
    将输入文本转换为大写
    
    Args:
        input_text (str): 输入的文本内容
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 处理后的结果文本
    """
    
    if not input_text:
        return "没有输入文本"
    
    # 转换为大写
    result = input_text.upper()
    
    return f"大写转换结果: {result}"