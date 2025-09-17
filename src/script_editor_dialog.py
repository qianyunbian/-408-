# 脚本编辑器对话框模块
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import os


class ScriptEditorDialog(QDialog):
    """脚本编辑器对话框"""
    def __init__(self, script_path: str, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.content_changed = False
        
        self.setWindowTitle(f"编辑脚本 - {os.path.basename(script_path)}")
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self._setup_ui()
        self._load_content()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 文件路径显示
        path_label = QLabel(f"文件路径: {self.script_path}")
        path_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #dee2e6;
            }
        """)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # 编辑器
        self.editor = QPlainTextEdit()
        
        # 设置等宽字体
        font = QFont("Consolas", 11)
        if not font.exactMatch():
            font = QFont("Monaco", 11)
        if not font.exactMatch():
            font = QFont("Courier New", 11)
        self.editor.setFont(font)
        
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                background-color: white;
                line-height: 1.4;
            }
            QPlainTextEdit:focus {
                border-color: #007bff;
            }
        """)
        
        # 监听内容变化
        self.editor.textChanged.connect(self._on_content_changed)
        
        layout.addWidget(self.editor)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        # 左侧按钮组
        left_button_layout = QHBoxLayout()
        
        # 打开外部编辑器按钮
        external_button = QPushButton("用外部编辑器打开")
        external_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        external_button.clicked.connect(self._open_external_editor)
        left_button_layout.addWidget(external_button)
        
        left_button_layout.addStretch()
        button_layout.addLayout(left_button_layout)
        
        # 右侧按钮组
        right_button_layout = QHBoxLayout()
        
        # 取消按钮
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
        cancel_button.clicked.connect(self._on_cancel)
        right_button_layout.addWidget(cancel_button)
        
        # 保存按钮
        save_button = QPushButton("保存")
        save_button.setFixedSize(80, 35)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_button.clicked.connect(self._save_content)
        right_button_layout.addWidget(save_button)
        
        button_layout.addLayout(right_button_layout)
        layout.addLayout(button_layout)
        
    def _load_content(self):
        """加载文件内容"""
        try:
            if os.path.exists(self.script_path):
                with open(self.script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.setPlainText(content)
                self.content_changed = False
            else:
                QMessageBox.warning(self, "错误", f"文件不存在: {self.script_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件: {e}")
            
    def _on_content_changed(self):
        """内容变化时的处理"""
        self.content_changed = True
        # 更新窗口标题显示修改状态
        title = f"编辑脚本 - {os.path.basename(self.script_path)}"
        if self.content_changed:
            title += " *"
        self.setWindowTitle(title)
        
    def _save_content(self):
        """保存内容"""
        try:
            content = self.editor.toPlainText()
            with open(self.script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.content_changed = False
            QMessageBox.information(self, "成功", "文件已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
            
    def _on_cancel(self):
        """取消操作"""
        if self.content_changed:
            reply = QMessageBox.question(
                self, "确认", 
                "文件内容已修改，确定要放弃更改吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        self.reject()
        
    def _open_external_editor(self):
        """用外部编辑器打开"""
        import subprocess
        import sys
        
        try:
            if sys.platform == "win32":
                # Windows
                os.startfile(self.script_path)
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(["open", self.script_path])
            else:
                # Linux 和其他 Unix 系统
                subprocess.run(["xdg-open", self.script_path])
                
            QMessageBox.information(self, "提示", "已尝试用外部编辑器打开文件")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开外部编辑器: {e}")
            
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.content_changed:
            reply = QMessageBox.question(
                self, "确认", 
                "文件内容已修改，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        event.accept()