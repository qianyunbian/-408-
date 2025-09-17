# 文本格式化示例
# 对输入文本进行多种格式化处理

def process(input_text, input_source, output_target):
    """
    对文本进行格式化处理
    
    Args:
        input_text (str): 输入的文本内容
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 格式化后的文本
    """
    
    if not input_text:
        return "请提供要格式化的文本"
    
    import re
    import json
    
    result = f"原始文本: {input_text}\n\n"
    result += "=== 格式化选项 ===\n"
    
    # 基本格式化
    result += f"1. 大写: {input_text.upper()}\n"
    result += f"2. 小写: {input_text.lower()}\n"
    result += f"3. 标题格式: {input_text.title()}\n"
    result += f"4. 首字母大写: {input_text.capitalize()}\n"
    
    # 清理格式化
    cleaned = re.sub(r'\s+', ' ', input_text.strip())
    result += f"5. 清理空格: {cleaned}\n"
    
    # 特殊格式化
    words = input_text.split()
    result += f"6. 反转单词: {' '.join(reversed(words))}\n"
    result += f"7. 字符反转: {input_text[::-1]}\n"
    result += f"8. 单词计数: {len(words)} 个单词\n"
    result += f"9. 字符计数: {len(input_text)} 个字符\n"
    
    # 编程格式化
    snake_case = re.sub(r'[^a-zA-Z0-9]+', '_', input_text).lower().strip('_')
    camel_case = ''.join(word.capitalize() for word in re.split(r'[^a-zA-Z0-9]+', input_text) if word)
    kebab_case = re.sub(r'[^a-zA-Z0-9]+', '-', input_text).lower().strip('-')
    
    result += f"10. snake_case: {snake_case}\n"
    result += f"11. CamelCase: {camel_case}\n"
    result += f"12. kebab-case: {kebab_case}\n"
    
    # 如果是JSON格式，尝试格式化
    try:
        parsed_json = json.loads(input_text)
        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        result += f"13. JSON格式化:\n{formatted_json}\n"
    except json.JSONDecodeError:
        result += "13. JSON格式化: 输入不是有效的JSON\n"
    
    # 编码相关
    try:
        import base64
        import urllib.parse
        
        # Base64编码
        b64_encoded = base64.b64encode(input_text.encode('utf-8')).decode('utf-8')
        result += f"14. Base64编码: {b64_encoded}\n"
        
        # URL编码
        url_encoded = urllib.parse.quote(input_text)
        result += f"15. URL编码: {url_encoded}\n"
        
    except Exception:
        pass
    
    return result