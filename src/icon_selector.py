# 图标选择器对话框
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QScrollArea, QWidget, QDialogButtonBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from .icon_manager import icon_manager

class IconSelector(QDialog):
    """图标选择器对话框"""
    
    def __init__(self, available_icons: List[str], parent=None):
        super().__init__(parent)
        self.available_icons = available_icons
        self.selected_icon = None
        self.icon_buttons = []
        
        self.setWindowTitle("选择图标")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("选择一个图标:")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        
        # 添加图标按钮
        cols = 6
        for i, icon_name in enumerate(self.available_icons):
            row = i // cols
            col = i % cols
            
            icon_btn = QPushButton()
            icon_btn.setFixedSize(60, 60)
            icon_btn.setToolTip(icon_name)
            
            # 设置图标
            icon = icon_manager.get_icon(icon_name, QSize(32, 32))
            if not icon.isNull():
                icon_btn.setIcon(icon)
                icon_btn.setIconSize(QSize(32, 32))
            else:
                icon_btn.setText(icon_name[:2].upper())
                
            icon_btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    background: white;
                }
                QPushButton:hover {
                    border-color: #4f7cff;
                    background: #f0f8ff;
                }
                QPushButton:checked {
                    border-color: #4f7cff;
                    background: #e0f0ff;
                    border-width: 3px;
                }
            """)
            
            icon_btn.setCheckable(True)
            icon_btn.clicked.connect(lambda checked, name=icon_name: self.select_icon(name))
            
            self.icon_buttons.append((icon_btn, icon_name))
            scroll_layout.addWidget(icon_btn, row, col)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 按钮框
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 初始状态下OK按钮不可用
        button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        
    def select_icon(self, icon_name: str):
        """选择图标"""
        # 取消其他按钮的选中状态
        for btn, name in self.icon_buttons:
            btn.setChecked(name == icon_name)
            
        self.selected_icon = icon_name
        self.ok_button.setEnabled(True)
        
    def get_selected_icon(self) -> Optional[str]:
        """获取选中的图标"""
        return self.selected_icon