# 动作编辑对话框模块
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QComboBox, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
import os
import subprocess
import sys
from .config_manager import config_manager


class ActionEditDialog(QDialog):
    """通用动作编辑对话框"""
    def __init__(self, action_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.action_config = action_config.copy()  # 复制原配置
        self.original_config = action_config  # 保存原始引用
        self.action_type = action_config.get("type", "")
        
        # 初始化所有可能的实例变量
        self.name_input: QLineEdit
        self.icon_input: QLineEdit
        self.hotkey_input: QLineEdit
        self.config_widget: QWidget
        self.config_layout: QVBoxLayout
        
        # 类型特定的控件（可选）
        self.command_input: Optional[QTextEdit] = None
        self.command_line_input: Optional[QLineEdit] = None  # 用于程序路径
        self.url_input: Optional[QLineEdit] = None
        self.text_input: Optional[QTextEdit] = None
        self.input_source_combo: Optional[QComboBox] = None
        self.output_target_combo: Optional[QComboBox] = None
        self.script_input: Optional[QLineEdit] = None
        
        self.setWindowTitle(f"编辑动作 - {action_config.get('name', '未命名')}")
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题样式
        title_style = "font-size: 14px; font-weight: bold; color: #333; margin-bottom: 10px;"
        label_style = "font-size: 12px; color: #555; margin-bottom: 5px;"
        input_style = """
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #007bff;
            }
        """
        
        # 基本信息区域
        basic_group = QWidget()
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setContentsMargins(0, 0, 0, 0)
        
        # 动作名称
        name_label = QLabel("动作名称:")
        name_label.setStyleSheet(label_style)
        basic_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(input_style)
        self.name_input.setPlaceholderText("请输入动作名称")
        basic_layout.addWidget(self.name_input)
        
        # 图标路径
        icon_label = QLabel("图标路径:")
        icon_label.setStyleSheet(label_style)
        basic_layout.addWidget(icon_label)
        
        icon_layout = QHBoxLayout()
        self.icon_input = QLineEdit()
        self.icon_input.setStyleSheet(input_style)
        self.icon_input.setPlaceholderText("留空使用默认图标")
        icon_layout.addWidget(self.icon_input)
        
        icon_button = QPushButton("选择")
        icon_button.setFixedSize(60, 32)
        icon_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        icon_button.clicked.connect(self._select_icon)
        icon_layout.addWidget(icon_button)
        
        basic_layout.addLayout(icon_layout)
        
        # 热键
        hotkey_label = QLabel("快捷键:")
        hotkey_label.setStyleSheet(label_style)
        basic_layout.addWidget(hotkey_label)
        
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setStyleSheet(input_style)
        self.hotkey_input.setPlaceholderText("如: ctrl+alt+c")
        basic_layout.addWidget(self.hotkey_input)
        
        layout.addWidget(basic_group)
        
        # 分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #eee;")
        layout.addWidget(separator)
        
        # 动作类型特定配置区域
        type_label = QLabel(f"动作类型配置 ({self._get_type_name()})")
        type_label.setStyleSheet(title_style)
        layout.addWidget(type_label)
        
        # 创建动态配置区域
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self._setup_type_specific_ui()
        layout.addWidget(self.config_widget)
        
        layout.addStretch()
        
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
        
        save_button = QPushButton("保存")
        save_button.setFixedSize(80, 35)
        save_button.setStyleSheet("""
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
        save_button.clicked.connect(self._save_changes)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
    def _get_type_name(self) -> str:
        """获取动作类型名称"""
        type_names = {
            "key": "模拟按键",
            "program": "运行程序",
            "url": "打开网址",
            "text": "发送文本",
            "panel": "子页面",
            "input_output": "输入输出"
        }
        return type_names.get(self.action_type, "未知类型")
        
    def _setup_type_specific_ui(self):
        """根据动作类型设置特定的UI"""
        label_style = "font-size: 12px; color: #555; margin-bottom: 5px;"
        input_style = """
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #007bff;
            }
        """
        
        if self.action_type == "key":
            # 模拟按键
            command_label = QLabel("按键序列:")
            command_label.setStyleSheet(label_style)
            self.config_layout.addWidget(command_label)
            
            self.command_input = QTextEdit()
            self.command_input.setStyleSheet(input_style)
            self.command_input.setMaximumHeight(100)
            self.command_input.setPlaceholderText("支持格式:\n• 组合键: ctrl+c, alt+tab\n• 单个按键: f5, enter\n• 文本串: \"hello world\"\n• 延时: wait(1000)")
            self.config_layout.addWidget(self.command_input)
            
        elif self.action_type == "program":
            # 运行程序
            command_label = QLabel("程序路径:")
            command_label.setStyleSheet(label_style)
            self.config_layout.addWidget(command_label)
            
            self.command_line_input = QLineEdit()
            self.command_line_input.setStyleSheet(input_style)
            self.command_line_input.setPlaceholderText("如: notepad.exe 或完整路径")
            self.config_layout.addWidget(self.command_line_input)
            
        elif self.action_type == "url":
            # 打开网址
            url_label = QLabel("网址 (URL):")
            url_label.setStyleSheet(label_style)
            self.config_layout.addWidget(url_label)
            
            self.url_input = QLineEdit()
            self.url_input.setStyleSheet(input_style)
            self.url_input.setPlaceholderText("如: https://www.google.com")
            self.config_layout.addWidget(self.url_input)
            
        elif self.action_type == "text":
            # 发送文本
            text_label = QLabel("文本内容:")
            text_label.setStyleSheet(label_style)
            self.config_layout.addWidget(text_label)
            
            self.text_input = QTextEdit()
            self.text_input.setStyleSheet(input_style)
            self.text_input.setMaximumHeight(150)
            self.text_input.setPlaceholderText("要发送的文本内容")
            self.config_layout.addWidget(self.text_input)
            
        elif self.action_type == "input_output":
            # 输入输出动作
            # 输入源
            input_label = QLabel("输入源:")
            input_label.setStyleSheet(label_style)
            self.config_layout.addWidget(input_label)
            
            self.input_source_combo = QComboBox()
            self.input_source_combo.setStyleSheet(input_style)
            input_options = [
                ("剪贴板内容", "clipboard"),
                ("鼠标选中文本", "selection"),
                ("手动输入", "manual"),
                ("无输入", "none")
            ]
            for text, value in input_options:
                self.input_source_combo.addItem(text, value)
            self.config_layout.addWidget(self.input_source_combo)
            
            # 输出目标
            output_label = QLabel("输出目标:")
            output_label.setStyleSheet(label_style)
            self.config_layout.addWidget(output_label)
            
            self.output_target_combo = QComboBox()
            self.output_target_combo.setStyleSheet(input_style)
            output_options = [
                ("发送文本", "text"),
                ("打开网址", "url"),
                ("复制到剪贴板", "clipboard"),
                ("保存到文件", "file"),
                ("显示窗口", "window")
            ]
            for text, value in output_options:
                self.output_target_combo.addItem(text, value)
            self.config_layout.addWidget(self.output_target_combo)
            
            # 脚本文件路径（只读显示）
            script_label = QLabel("脚本文件:")
            script_label.setStyleSheet(label_style)
            self.config_layout.addWidget(script_label)
            
            script_file_layout = QHBoxLayout()
            
            self.script_input = QLineEdit()
            self.script_input.setStyleSheet(input_style + "QLineEdit { background-color: #f8f9fa; }")
            self.script_input.setReadOnly(True)
            self.script_input.setPlaceholderText("脚本文件路径 (只读)")
            script_file_layout.addWidget(self.script_input)
            
            # 添加编辑脚本按钮
            edit_script_button = QPushButton("编辑脚本")
            edit_script_button.setFixedSize(80, 32)
            edit_script_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            edit_script_button.clicked.connect(self._edit_script_file)
            script_file_layout.addWidget(edit_script_button)
            
            self.config_layout.addLayout(script_file_layout)
            
        elif self.action_type == "panel":
            # 子页面 - 显示提示信息
            info_label = QLabel("子页面动作配置:")
            info_label.setStyleSheet(label_style)
            self.config_layout.addWidget(info_label)
            
            info_text = QLabel("子页面的动作内容需要在子页面中进行管理")
            info_text.setStyleSheet("color: #6c757d; font-style: italic; padding: 10px; background-color: #f8f9fa; border-radius: 4px;")
            info_text.setWordWrap(True)
            self.config_layout.addWidget(info_text)
    
    def _load_data(self):
        """加载数据到界面"""
        # 基本信息
        self.name_input.setText(self.action_config.get("name", ""))
        self.icon_input.setText(self.action_config.get("icon_path", ""))
        self.hotkey_input.setText(self.action_config.get("hotkey", ""))
        
        # 根据类型加载特定数据
        if self.action_type == "key" and self.command_input:
            self.command_input.setPlainText(self.action_config.get("command", ""))
            
        elif self.action_type == "program" and self.command_line_input:
            self.command_line_input.setText(self.action_config.get("command", ""))
            
        elif self.action_type == "url" and self.url_input:
            self.url_input.setText(self.action_config.get("url", ""))
            
        elif self.action_type == "text" and self.text_input:
            self.text_input.setPlainText(self.action_config.get("text", ""))
            
        elif self.action_type == "input_output":
            if self.input_source_combo:
                # 设置输入源
                input_source = self.action_config.get("input_source", "clipboard")
                for i in range(self.input_source_combo.count()):
                    if self.input_source_combo.itemData(i) == input_source:
                        self.input_source_combo.setCurrentIndex(i)
                        break
                        
            if self.output_target_combo:
                # 设置输出目标
                output_target = self.action_config.get("output_target", "text")
                for i in range(self.output_target_combo.count()):
                    if self.output_target_combo.itemData(i) == output_target:
                        self.output_target_combo.setCurrentIndex(i)
                        break
                        
            if self.script_input:
                # 显示脚本文件
                self.script_input.setText(self.action_config.get("script_file", ""))
    
    def _select_icon(self):
        """选择图标"""
        from .icon_manager import icon_manager
        available_icons = icon_manager.get_available_icons()
        if not available_icons:
            QMessageBox.information(self, "提示", "没有可用的图标文件")
            return
            
        # 创建图标选择对话框
        from .icon_selector import IconSelector
        dialog = IconSelector(available_icons, self)
        if dialog.exec() == IconSelector.DialogCode.Accepted:
            selected_icon = dialog.get_selected_icon()
            if selected_icon:
                self.icon_input.setText(selected_icon)
    
    def _save_changes(self):
        """保存更改"""
        try:
            # 基本信息
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "错误", "动作名称不能为空")
                return
                
            self.action_config["name"] = name
            self.action_config["icon_path"] = self.icon_input.text().strip()
            self.action_config["hotkey"] = self.hotkey_input.text().strip()
            
            # 根据类型保存特定数据
            if self.action_type == "key" and self.command_input:
                command = self.command_input.toPlainText().strip()
                if not command:
                    QMessageBox.warning(self, "错误", "按键序列不能为空")
                    return
                self.action_config["command"] = command
                
            elif self.action_type == "program" and self.command_line_input:
                command = self.command_line_input.text().strip()
                if not command:
                    QMessageBox.warning(self, "错误", "程序路径不能为空")
                    return
                self.action_config["command"] = command
                
            elif self.action_type == "url" and self.url_input:
                url = self.url_input.text().strip()
                if not url:
                    QMessageBox.warning(self, "错误", "网址不能为空")
                    return
                self.action_config["url"] = url
                
            elif self.action_type == "text" and self.text_input:
                text = self.text_input.toPlainText().strip()
                if not text:
                    QMessageBox.warning(self, "错误", "文本内容不能为空")
                    return
                self.action_config["text"] = text
                
            elif self.action_type == "input_output":
                if self.input_source_combo and self.output_target_combo:
                    input_source = self.input_source_combo.currentData()
                    output_target = self.output_target_combo.currentData()
                    self.action_config["input_source"] = input_source
                    self.action_config["output_target"] = output_target
                    # 脚本文件路径不允许编辑
            
            # 更新原始配置
            self.original_config.update(self.action_config)
            
            # 刷新快捷键注册
            self._refresh_hotkeys()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
            
    def _refresh_hotkeys(self):
        """刷新快捷键注册"""
        try:
            # 保存配置并设置标记需要刷新热键
            from .config_manager import config_manager
            config_manager.save_config()  
            
            # 尝试直接刷新热键（如果能找到主程序实例）
            # 这里用一个简单的方式：设置一个全局标记
            import os
            os.environ['QUICKERING_HOTKEYS_NEED_REFRESH'] = '1'
            print("[DEBUG] 已标记快捷键需要刷新")
        except Exception as e:
            print(f"刷新快捷键失败: {e}")
    
    def _edit_script_file(self):
        """编辑脚本文件"""
        if not hasattr(self, 'script_input') or not self.script_input:
            return
            
        script_file = self.script_input.text().strip()
        if not script_file:
            QMessageBox.warning(self, "错误", "未找到脚本文件路径")
            return
            
        # 获取完整的文件路径
        script_path = config_manager.get_input_output_script_path(script_file)
        
        if not script_path.exists():
            QMessageBox.warning(self, "错误", f"脚本文件不存在: {script_path}")
            return
            
        try:
            # 尝试使用默认编辑器打开文件
            script_path_str = str(script_path)
            if sys.platform == "win32":
                # Windows
                os.startfile(script_path_str)
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(["open", script_path_str])
            else:
                # Linux 和其他 Unix 系统
                subprocess.run(["xdg-open", script_path_str])
                
        except Exception as e:
            # 如果默认编辑器失败，使用内置编辑器
            try:
                from .script_editor_dialog import ScriptEditorDialog
                dialog = ScriptEditorDialog(str(script_path), self)
                dialog.exec()
            except Exception as e2:
                QMessageBox.warning(self, "错误", f"无法打开文件编辑器: {e2}\n\n文件路径: {script_path}")
    
    def get_updated_config(self) -> Dict[str, Any]:
        """获取更新后的配置"""
        return self.action_config