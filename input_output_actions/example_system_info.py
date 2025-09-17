# 系统信息获取示例
# 无需输入，自动获取系统信息

# 在文件顶部尝试导入psutil，避免IDE检查问题
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore
    HAS_PSUTIL = False

def process(input_text, input_source, output_target):
    """
    获取系统信息
    
    Args:
        input_text (str): 输入的文本内容（此脚本忽略输入）
        input_source (str): 输入源 (clipboard/selection/manual/none)
        output_target (str): 输出目标 (text/url/clipboard/file/window)
    
    Returns:
        str: 系统信息
    """
    
    import datetime
    import platform
    import os
    
    try:
        # 获取系统基本信息
        system_info = {
            '时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '操作系统': f"{platform.system()} {platform.release()}",
            'Python版本': platform.python_version(),
            '处理器': platform.processor(),
            '机器类型': platform.machine(),
            '用户名': os.getlogin(),
            '当前目录': os.getcwd()
        }
        
        # 如果psutil可用，获取更详细的系统信息
        if HAS_PSUTIL and psutil is not None:
            try:
                # 获取内存信息
                memory = psutil.virtual_memory()
                system_info['内存总量'] = f"{memory.total // (1024**3)} GB"
                system_info['内存使用率'] = f"{memory.percent}%"
                
                # 获取磁盘信息（Windows使用C盘）
                disk_path = 'C:\\' if platform.system() == 'Windows' else '/'
                disk = psutil.disk_usage(disk_path)
                system_info['磁盘总量'] = f"{disk.total // (1024**3)} GB"
                system_info['磁盘使用率'] = f"{disk.percent}%"
            except Exception as psutil_error:
                system_info['psutil错误'] = f"无法获取详细信息: {str(psutil_error)}"
        else:
            system_info['提示'] = "安装psutil库可获取更详细的系统信息: pip install psutil"
        
        # 格式化输出
        result = "=== 系统信息 ===\n"
        for key, value in system_info.items():
            result += f"{key}: {value}\n"
            
        return result
        
    except Exception as e:
        return f"获取系统信息失败: {str(e)}"