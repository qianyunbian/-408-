# 输入输出动作创建对话框模块
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QComboBox, QWidget, QMessageBox,
    QTabWidget, QPlainTextEdit
)
from PySide6.QtCore import Qt
import uuid


class InputOutputActionDialog(QDialog):
    """输入输出动作创建对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_data = None
        
        self.setWindowTitle("创建输入输出动作")
        self.setModal(True)
        self.resize(800, 650)
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 动作名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("动作名称："))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入动作名称")
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 输入源选择
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入源："))
        self.input_source = QComboBox()
        input_options = [
            ("剪贴板内容", "clipboard"),
            ("鼠标选中文本", "selection"),
            ("手动输入", "manual"),
            ("无输入", "none")
        ]
        for text, value in input_options:
            self.input_source.addItem(text, value)
        self.input_source.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                min-width: 150px;
            }
        """)
        input_layout.addWidget(self.input_source)
        input_layout.addStretch()
        layout.addLayout(input_layout)
        
        # 输出目标选择
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目标："))
        self.output_target = QComboBox()
        output_options = [
            ("发送文本", "text"),
            ("打开网址", "url"),
            ("复制到剪贴板", "clipboard"),
            ("保存到文件", "file"),
            ("显示窗口", "window")
        ]
        for text, value in output_options:
            self.output_target.addItem(text, value)
        self.output_target.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                min-width: 150px;
            }
        """)
        output_layout.addWidget(self.output_target)
        output_layout.addStretch()
        layout.addLayout(output_layout)
        
        # 功能描述
        layout.addWidget(QLabel("功能描述："))
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("请描述这个输入输出动作的功能...")
        self.description_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.description_input)
        
        # Python脚本编辑器 - 使用标签页
        layout.addWidget(QLabel("Python脚本代码："))
        
        # 创建标签页组件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
                color: #007bff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # 自定义脚本标签页
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        custom_layout.setContentsMargins(10, 10, 10, 10)
        
        custom_hint = QLabel("自定义脚本，实现任意功能")
        custom_hint.setStyleSheet("color: #6c757d; font-style: italic; margin-bottom: 10px;")
        custom_layout.addWidget(custom_hint)
        
        self.script_editor = QPlainTextEdit()
        self.script_editor.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        self.script_editor.setPlainText(self._get_custom_template())
        custom_layout.addWidget(self.script_editor)
        
        self.tab_widget.addTab(custom_tab, "自定义")
        
        # 添加示例标签页
        self._add_example_tabs()
        
        layout.addWidget(self.tab_widget)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("取消")
        cancel_button.setFixedSize(80, 35)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        create_button = QPushButton("创建")
        create_button.setFixedSize(80, 35)
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        create_button.clicked.connect(self._create_action)
        button_layout.addWidget(create_button)
        
        layout.addLayout(button_layout)
        
        # 默认选中第一个标签页
        self.tab_widget.setCurrentIndex(0)
        
    def _add_example_tabs(self):
        """添加示例标签页"""
        examples = [
            {
                "title": "文本处理",
                "description": "对输入文本进行各种处理操作",
                "script": self._get_text_processing_example()
            },
            {
                "title": "系统信息",
                "description": "获取各种系统信息和状态",
                "script": self._get_system_info_example()
            },
            {
                "title": "网络查询",
                "description": "执行网络查询和获取在线数据",
                "script": self._get_network_example()
            }
        ]
        
        for example in examples:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(10, 10, 10, 10)
            
            # 示例描述
            desc_label = QLabel(example["description"])
            desc_label.setStyleSheet("color: #6c757d; font-style: italic; margin-bottom: 10px;")
            tab_layout.addWidget(desc_label)
            
            # 示例代码
            example_editor = QPlainTextEdit()
            example_editor.setStyleSheet("""
                QPlainTextEdit {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    line-height: 1.4;
                    background-color: #f8f9fa;
                }
            """)
            example_editor.setPlainText(example["script"])
            example_editor.setReadOnly(True)
            tab_layout.addWidget(example_editor)
            
            # 使用此示例按钮
            use_button = QPushButton(f"使用此示例")
            use_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 12px;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            use_button.clicked.connect(lambda checked, script=example["script"]: self._use_example(script))
            tab_layout.addWidget(use_button)
            
            self.tab_widget.addTab(tab_widget, example["title"])
    
    def _use_example(self, script_content: str):
        """使用示例代码"""
        self.script_editor.setPlainText(script_content)
        self.tab_widget.setCurrentIndex(0)  # 切换到自定义标签页
    
    def _get_custom_template(self) -> str:
        """获取自定义模板"""
        return '''# 输入输出动作脚本
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
'''
        
    def _get_text_processing_example(self) -> str:
        """文本处理示例"""
        return '''def process(input_text, input_source, output_target):
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
    
    return "\\n".join(result)
'''
        
    def _get_system_info_example(self) -> str:
        """系统信息示例"""
        return '''def process(input_text, input_source, output_target):
    """系统信息获取示例"""
    import datetime
    import platform
    import os
    
    try:
        # 基本系统信息
        info = []
        info.append("=== 系统信息 ===")
        info.append(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        info.append(f"操作系统: {platform.system()} {platform.release()}")
        info.append(f"Python版本: {platform.python_version()}")
        info.append(f"处理器: {platform.processor()}")
        info.append(f"机器类型: {platform.machine()}")
        info.append(f"用户名: {os.getlogin()}")
        info.append(f"当前目录: {os.getcwd()}")
        
        # 尝试获取更多信息
        try:
            import psutil
            memory = psutil.virtual_memory()
            info.append(f"内存使用率: {memory.percent}%")
            info.append(f"可用内存: {memory.available // (1024**3)} GB")
        except ImportError:
            info.append("提示: 安装psutil库可获取更多信息")
        
        return "\\n".join(info)
        
    except Exception as e:
        return f"获取系统信息失败: {e}"
'''
        
    def _get_network_example(self) -> str:
        """网络查询示例"""
        return '''def process(input_text, input_source, output_target):
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
            return "\\n".join(result)
        else:
            return f"查询失败: {data.get('message', '未知错误')}"
            
    except Exception as e:
        return f"网络查询失败: {e}\\n\\n提示: 请检查网络连接"
'''
        
    def _create_action(self):
        """创建动作"""
        try:
            # 获取动作名称
            action_name = self.name_input.text().strip()
            if not action_name:
                QMessageBox.warning(self, "错误", "请输入动作名称")
                return
            
            # 获取表单数据
            script_content = self.script_editor.toPlainText().strip()
            description = self.description_input.toPlainText().strip()
            input_source = self.input_source.currentData()
            output_target = self.output_target.currentData()
            
            if not script_content:
                QMessageBox.warning(self, "错误", "请输入Python脚本代码")
                return
                
            # 创建动作配置
            action_id = str(uuid.uuid4())
            
            # 保存脚本文件
            from .config_manager import config_manager
            script_filename = config_manager.create_input_output_script(action_name, action_id, script_content)
            if not script_filename:
                QMessageBox.warning(self, "错误", "创建脚本文件失败")
                return
                
            # 创建动作配置
            self.action_data = config_manager.create_action(
                action_name,
                "input_output",
                script_file=script_filename,
                input_source=input_source,
                output_target=output_target,
                description=description
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建动作失败: {e}")
            
    def get_action_data(self) -> Optional[Dict[str, Any]]:
        """获取创建的动作数据"""
        return self.action_data