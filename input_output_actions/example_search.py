# 智能搜索示例
# 将输入文本作为搜索关键词，生成搜索URL

def process(input_text, input_source, output_target):
    """
    生成搜索URL
    
    Args:
        input_text (str): 输入的文本内容（搜索关键词）
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 生成的搜索URL
    """
    
    if not input_text:
        # 无输入时返回默认搜索页面
        return "https://www.google.com"
    
    # 处理搜索关键词
    keywords = input_text.strip().replace(' ', '+')
    
    # 生成多个搜索引擎的URL
    search_urls = {
        'Google': f"https://www.google.com/search?q={keywords}",
        'Bing': f"https://www.bing.com/search?q={keywords}",
        'DuckDuckGo': f"https://duckduckgo.com/?q={keywords}",
        'GitHub': f"https://github.com/search?q={keywords}",
        'Stack Overflow': f"https://stackoverflow.com/search?q={keywords}"
    }
    
    # 根据输出目标返回不同格式
    if output_target == "url":
        # 直接返回Google搜索URL用于打开
        return search_urls['Google']
    elif output_target == "window":
        # 返回所有搜索URL的列表
        result = f"搜索关键词: {input_text}\n\n可用的搜索链接:\n"
        for engine, url in search_urls.items():
            result += f"• {engine}: {url}\n"
        return result
    else:
        # 返回Google搜索URL
        return search_urls['Google']