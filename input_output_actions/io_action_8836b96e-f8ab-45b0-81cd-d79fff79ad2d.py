# 输入输出动作脚本
# 可用变量:
# - input_text: 输入文本内容
# - input_source: 输入源类型
# - output_target: 输出目标类型

def process(input_text, input_source, output_target):
    """
    处理输入文本并返回结果
    
    Args:
        input_text (str): 输入的文本内容
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 处理后的结果文本
    """
    
    # 在这里编写你的代码
    if input_text:
        return f"处理结果: {input_text}"
    else:
        return "没有输入内容"