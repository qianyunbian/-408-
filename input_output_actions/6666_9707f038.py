def process(input_text, input_source, output_target):
    """文本处理示例"""
    
    if not input_text:
        return "请提供要处理的文本"
    
    # 文本处理操作
    result = []
    result.append(f"原始文本: {input_text}")
    result.append(f"大写: {input_text.upper()}")
    result.append(f"小写: {input_text.lower()}")
    result.append(f"首字母大写: {input_text.title()}")
    result.append(f"反转: {input_text[::-1]}")
    result.append(f"字数统计: {len(input_text)} 个字符")
    result.append(f"单词数: {len(input_text.split())} 个单词")
    
    return "\n".join(result)
