def process(input_text, input_source, output_target):
    """网络查询示例"""
    import urllib.request
    import json
    
    try:
        # 如果有输入，尝试作为IP地址查询
        if input_text and input_text.strip():
            ip = input_text.strip()
            url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        else:
            # 无输入时查询本机IP
            url = "http://ip-api.com/json/?lang=zh-CN"
        
        # 发起网络请求
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        if data["status"] == "success":
            result = []
            result.append("=== IP信息 ===")
            result.append(f"IP地址: {data.get('query', 'N/A')}")
            result.append(f"国家: {data.get('country', 'N/A')}")
            result.append(f"地区: {data.get('regionName', 'N/A')}")
            result.append(f"城市: {data.get('city', 'N/A')}")
            result.append(f"ISP: {data.get('isp', 'N/A')}")
            result.append(f"时区: {data.get('timezone', 'N/A')}")
            return "\n".join(result)
        else:
            return f"查询失败: {data.get('message', '未知错误')}"
            
    except Exception as e:
        return f"网络查询失败: {e}\n\n提示: 请检查网络连接"