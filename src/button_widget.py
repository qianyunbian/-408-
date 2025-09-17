# 按钮组件模块
from typing import Callable, Optional, Dict, Any, TYPE_CHECKING
from PySide6.QtWidgets import QPushButton, QMenu, QInputDialog, QMessageBox, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QCursor, QAction, QPixmap, QIcon
from .config_manager import config_manager
from .icon_manager import icon_manager

if TYPE_CHECKING:
    from .action_panel import ActionPanel

class DraggableButton(QWidget):
    """可拖拽的动作按钮（使用QWidget实现真正的垂直布局）"""
    
    # 信号定义
    rename_requested = Signal(str)  # 请求重命名信号
    icon_change_requested = Signal(str)  # 请求更改图标信号
    delete_requested = Signal()  # 请求删除信号
    clicked = Signal()  # 点击信号（与QPushButton兼容）
    copy_requested = Signal()  # 请求复制信号
    cut_requested = Signal()  # 请求剪切信号
    edit_requested = Signal()  # 请求编辑信号
    
    def __init__(self, action_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.action_config = action_config
        self.action_id = action_config.get("id", "")
        self._is_dragging = False
        self.start_pos = None
        self._is_hovered = False
        
        self.setup_ui()
        self.setup_context_menu()
        
    def setup_ui(self):
        """设置UI（使用QWidget+QVBoxLayout实现真正的垂直布局）"""
        btn_config = config_manager.get("action_buttons", {})
        style_config = btn_config.get("style", {})
        
        size = btn_config.get("size", 66)
        self.setFixedSize(size, size)
        
        # 强制设置背景填充
        self.setAutoFillBackground(True)
        
        # 强制设置样式属性
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 图标标签
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedHeight(int(size * 0.6))  # 图标区卆60%
        layout.addWidget(self.icon_label)
        
        # 文字标签
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)
        
        # 保存样式配置以便动态更新
        self.style_config = style_config
        
        # 初始样式
        self.update_style()
        self.update_display()
        
    def update_style(self):
        """更新样式（支持悬停效果）"""
        if self._is_hovered:
            bg_color = self.style_config.get("hover_background_color", "#e6f0ff")
            border_color = self.style_config.get("hover_border_color", "#4f7cff")
        else:
            bg_color = self.style_config.get("background_color", "#f8fbff")
            # 使用配置中的边框颜色，默认为蓝色
            border_color = "#4f7cff"  # 与控制按钮一致的蓝色边框
            
        font_size = self.style_config.get("font_size", 9)
        color = self.style_config.get("color", "#333")
        border_radius = self.style_config.get("border_radius", 12)
        
        # 使用更强制的QWidget样式设置，确保背景色显示（添加浅色边框）
        style = f"""
            DraggableButton {{
                background-color: {bg_color} !important;
                border: 1px solid #ddd !important;
                border-radius: {border_radius}px !important;
            }}
            QWidget {{
                background-color: {bg_color} !important;
                border: 1px solid #ddd !important;
                border-radius: {border_radius}px !important;
            }}
        """
        self.setStyleSheet(style)
        
        # 额外设置调色板确保背景生效
        from PySide6.QtGui import QPalette, QColor
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg_color))
        palette.setColor(QPalette.ColorRole.Base, QColor(bg_color))
        palette.setColor(QPalette.ColorRole.Button, QColor(bg_color))
        self.setPalette(palette)
        
        # 设置文字标签样式
        self.text_label.setStyleSheet(f"""
            QLabel {{
                font-size: {font_size}px;
                color: {color};
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        
        # 设置图标标签样式
        self.icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
                font-size: 20px;
            }
        """)
        
    def setup_context_menu(self):
        """设置右键菜单"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 编辑动作（新增）
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_action)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # 重命名动作
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self.rename_action)
        menu.addAction(rename_action)
        
        # 更改图标动作
        icon_action = QAction("更改图标", self)
        icon_action.triggered.connect(self.change_icon)
        menu.addAction(icon_action)
        
        menu.addSeparator()
        
        # 复制动作
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self.copy_action)
        menu.addAction(copy_action)
        
        # 剪切动作
        cut_action = QAction("剪切", self)
        cut_action.triggered.connect(self.cut_action)
        menu.addAction(cut_action)
        
        menu.addSeparator()
        
        # 删除动作
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_action)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec(self.mapToGlobal(position))
        
    def rename_action(self):
        """重命名动作"""
        current_name = self.action_config.get("name", "")
        new_name, ok = QInputDialog.getText(
            self, "重命名动作", "请输入新名称:", text=current_name
        )
        
        if ok and new_name.strip() and new_name.strip() != current_name:
            self.action_config["name"] = new_name.strip()
            self.update_display()
            self.rename_requested.emit(self.action_id)
            
    def change_icon(self):
        """更改图标"""
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
                self.action_config["icon_path"] = selected_icon
                self.update_display()
                self.icon_change_requested.emit(self.action_id)
                
    def delete_action(self):
        """删除动作"""
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除动作 '{self.action_config.get('name', '')}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit()
            
    def copy_action(self):
        """复制动作"""
        self.copy_requested.emit()
        
    def cut_action(self):
        """剪切动作"""
        self.cut_requested.emit()
        
    def edit_action(self):
        """编辑动作"""
        self.edit_requested.emit()
            
    def update_display(self):
        """更新显示内容（实现真正的垂直布局：图标在上文字在下）"""
        name = self.action_config.get("name", "未命名")
        action_type = self.action_config.get("type", "")
        icon_path = self.action_config.get("icon_path", "")
        
        # 如果有自定义SVG图标路径，尝试使用SVG图标
        if icon_path and icon_manager.has_icon(icon_path):
            try:
                from PySide6.QtCore import QSize
                from PySide6.QtGui import QPixmap
                
                # 加载SVG图标并设置到图标标签
                icon = icon_manager.get_icon(icon_path, QSize(32, 32))
                if not icon.isNull():
                    pixmap = icon.pixmap(32, 32)
                    self.icon_label.setPixmap(pixmap)
                    self.text_label.setText(name)
                    return
            except Exception as e:
                print(f"加载SVG图标失败: {e}")
                # 如果加载失败，使用文本图标
                pass
                
        # 使用文本图标（emoji）垂直布局
        icon_text = self.get_type_icon(action_type)
        
        # 清除图片并设置文本图标
        from PySide6.QtGui import QPixmap
        self.icon_label.setPixmap(QPixmap())  # 清除图片
        self.icon_label.setText(icon_text)
        self.text_label.setText(name)
        
    def get_type_icon(self, action_type: str) -> str:
        """根据动作类型获取图标（使用更大的emoji）"""
        type_icons = {
            "key": "⌨️",      # 键盘emoji
            "program": "⚙️",  # 齿轮emoji 
            "url": "🌐",       # 地球emoji
            "text": "📝",      # 笔记emoji
            "panel": "📁",     # 文件夹emoji
            "command": "⚡",    # 闪电emoji
            "clipboard": "📋", # 剪贴板emoji
            "input_output": "🔄", # 输入输出emoji
            "placeholder": "🔄" # 循环emoji
        }
        return type_icons.get(action_type, "🔘")  # 默认使用小圆点emoji
        
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovered = True
        self.update_style()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self.update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()
            self._is_dragging = False
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
            
        if (self.start_pos and 
            (event.position().toPoint() - self.start_pos).manhattanLength() >= 10):
            
            self._is_dragging = True
            parent = self.parent()
            if hasattr(parent, '_dragged_button'):
                setattr(parent, '_dragged_button', self)
            
            # 高亮拖拽状态
            current_style = self.styleSheet()
            # 移除原有边框设置，添加拖拽样式
            new_style = current_style.replace("border: 1px solid", "border: 2px dashed")
            if "2px dashed" not in new_style:
                new_style += "border: 2px dashed #4f7cff;"
            self.setStyleSheet(new_style)
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                # 恢复正常样式
                self.update_style()
                
                # 处理拖拽结束逻辑
                parent = self.parent()
                if parent:
                    try:
                        # 使用 getattr 避免类型检查错误
                        mapFromGlobal = getattr(parent, 'mapFromGlobal', None)
                        if mapFromGlobal:
                            pos_in_panel = mapFromGlobal(event.globalPosition().toPoint())
                        else:
                            pos_in_panel = event.position().toPoint()
                        
                        # 调用父级对象的拖拽处理方法
                        handle_button_drop = getattr(parent, 'handle_button_drop', None)
                        if handle_button_drop:
                            handle_button_drop(self, pos_in_panel)
                    except Exception as e:
                        print(f"处理按钮拖拽失败: {e}")
                    
                self._is_dragging = False
            else:
                # 如果不是拖拽，则是点击
                self.clicked.emit()
                
        super().mouseReleaseEvent(event)