# 快捷发送面板对话框模块
import json
import os
import time
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QWidget, QMessageBox,
    QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QPainter, QFontMetrics
from .config_manager import config_manager


class ElidedLabel(QLabel):
    """支持文本省略显示的QLabel"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        # 使用Qt内置的文本省略功能
        self.setWordWrap(False)
        
    def setText(self, text: str):
        self._full_text = text
        # 直接设置文本，让Qt处理省略
        super().setText(text)
        
    def text(self) -> str:
        """返回完整文本，而不是显示的省略文本"""
        return self._full_text
        
    def resizeEvent(self, event):
        """窗口大小改变时重新计算文本显示"""
        super().resizeEvent(event)
        self._update_elided_text()
        
    def _update_elided_text(self):
        """更新省略文本显示"""
        if not self._full_text:
            return
            
        font_metrics = QFontMetrics(self.font())
        available_width = self.width() - 16  # 减去内边距
        
        if available_width > 0 and font_metrics.horizontalAdvance(self._full_text) > available_width:
            elided_text = font_metrics.elidedText(
                self._full_text, 
                Qt.TextElideMode.ElideRight, 
                available_width
            )
            # 使用父类方法设置显示文本
            super().setText(elided_text)
        else:
            super().setText(self._full_text)
        
    def get_full_text(self) -> str:
        """获取完整文本"""
        return self._full_text
        
    def is_text_elided(self) -> bool:
        """检查文本是否被省略"""
        if not self._full_text:
            return False
        font_metrics = QFontMetrics(self.font())
        available_width = self.width() - 16
        # 确保有有效的宽度
        return (available_width > 0 and 
                font_metrics.horizontalAdvance(self._full_text) > available_width)


class DraggableListWidget(QListWidget):
    """支持拖拽排序的列表控件"""
    item_moved = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
    def dropEvent(self, event):
        source_item = self.currentItem()
        if not source_item:
            return
        source_index = self.row(source_item)
        super().dropEvent(event)
        target_index = self.row(source_item)
        if source_index != target_index:
            self.item_moved.emit(source_index, target_index)


class SendButtonWidget(QWidget):
    """发送按钮控件"""
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    send_requested = Signal(str)
    content_changed = Signal()  # 新增：内容变化信号
    
    def __init__(self, item_data: Dict[str, Any], index: int, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.index = index
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_tooltip)
        self.editing_mode = False
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(10)
        
        # 左侧文本显示区域
        self.text_label = ElidedLabel(self.item_data.get("key", ""))
        self.text_label.setStyleSheet("""
            ElidedLabel {
                background-color: transparent;
                border: none;
                padding: 6px 8px;
                font-size: 12px;
                color: #333;
                border-radius: 4px;
            }
            ElidedLabel:hover {
                background-color: #e3f2fd;
                color: #1976d2;
                border: 1px solid #bbdefb;
            }
        """)
        # 通过Qt方法设置鼠标光标
        self.text_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text_label.setMinimumHeight(30)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 根据文本内容动态调整标签宽度
        text_content = self.item_data.get("key", "")
        # 设置最大和最小宽度限制，让文本标签能够响应式调整
        min_width = 80   # 设置最小宽度
        max_width = 300  # 设置最大宽度限制
        
        self.text_label.setMinimumWidth(min_width)
        # 不设置最大宽度限制，让它能够充分利用可用空间
        # self.text_label.setMaximumWidth(max_width)
        # 设置尺寸策略为Expanding，允许在可用空间内自由伸缩
        from PySide6.QtWidgets import QSizePolicy
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # 文本编辑框（默认隐藏）
        self.text_edit = QLineEdit()
        self.text_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #007bff;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 12px;
                background-color: white;
            }
        """)
        self.text_edit.setMinimumHeight(30)
        self.text_edit.setMinimumWidth(min_width)
        # 设置编辑框也使用相同的尺寸策略
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.text_edit.hide()  # 默认隐藏
        self.text_edit.editingFinished.connect(self._finish_editing)
        
        # 将文本显示和编辑框放在同一位置
        text_container = QWidget()
        # 设置容器的尺寸策略，允许它伸缩
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_edit)
        
        # 使用适中的伸缩因子，确保发送按钮可见
        layout.addWidget(text_container, 1)  # 降低伸缩因子
        
        # 不需要addStretch，直接让发送按钮在右侧
        
        # 右侧小按钮
        button_text = self.item_data.get("text", "发送")
        self.send_button = QPushButton(button_text)
        self.send_button.setFixedSize(60, 30)  # 缩小按钮尺寸
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        
        key_value = self.item_data.get("key", "")
        self.send_button.clicked.connect(lambda: self.send_requested.emit(key_value))
        
        layout.addWidget(self.send_button)
        
        # 设置整体样式
        self.setStyleSheet("""
            SendButtonWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px;
            }
            SendButtonWidget:hover {
                background-color: #e9ecef;
                border-color: #007bff;
            }
        """)
        
    def mousePressEvent(self, event):
        """鼠标点击事件 - 单击左键发送文本"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击位置是否在文本区域
            text_pos = self.text_label.mapFromParent(event.pos())
            if self.text_label.rect().contains(text_pos):
                # 单击文本区域直接发送
                key_value = self.item_data.get("key", "")
                self.send_requested.emit(key_value)
        super().mousePressEvent(event)
        
    def _start_editing(self):
        """开始编辑模式"""
        if not self.editing_mode:
            self.editing_mode = True
            current_text = self.text_label.text()
            self.text_edit.setText(current_text)
            
            # 切换显示
            self.text_label.hide()
            self.text_edit.show()
            self.text_edit.setFocus()
            self.text_edit.selectAll()
            
    def _finish_editing(self):
        """结束编辑模式"""
        if self.editing_mode:
            self.editing_mode = False
            new_text = self.text_edit.text().strip()
            
            if new_text:
                # 更新数据
                old_key = self.item_data.get("key", "")
                self.item_data["key"] = new_text
                self.text_label.setText(new_text)
                
                # 如果内容发生变化，更新发送函数并发出信号
                if old_key != new_text:
                    self.send_button.clicked.disconnect()
                    self.send_button.clicked.connect(lambda: self.send_requested.emit(new_text))
                    self.content_changed.emit()  # 发出内容变化信号
            else:
                # 如果为空，恢复原来的内容
                self.text_edit.setText(self.text_label.text())
            
            # 切换显示
            self.text_edit.hide()
            self.text_label.show()
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        edit_text_action = QAction("编辑文本内容", self)
        edit_text_action.triggered.connect(self._start_editing)
        menu.addAction(edit_text_action)
        
        edit_action = QAction("编辑按钮文字", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.index))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.index))
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())
        
    def resizeEvent(self, event):
        """窗口大小改变时通知文本标签更新"""
        super().resizeEvent(event)
        # 强制更新文本标签的显示
        if hasattr(self, 'text_label'):
            self.text_label._update_elided_text()
        
    def enterEvent(self, event):
        super().enterEvent(event)
        # 检查是否需要显示tooltip
        key_text = self.item_data.get("key", "")
        if key_text:
            # 如果文本长度大于50个字符，立即显示tooltip
            if len(key_text) > 50:
                self._show_tooltip()
            # 否则检查文本是否被省略或有自定义tooltip，延迟显示
            elif self.text_label.is_text_elided() or self.item_data.get("tooltip"):
                self.hover_timer.start(1000)
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hover_timer.stop()
        
    def _show_tooltip(self):
        key_text = self.item_data.get("key", "")
        tooltip_text = self.item_data.get("tooltip", "")
        
        # 优先显示自定义tooltip
        if tooltip_text:
            formatted_tooltip = self._format_tooltip(tooltip_text)
            self.setToolTip(formatted_tooltip)
        elif key_text:
            # 如果文本长度大于50个字符，格式化显示（每100字符换行）
            if len(key_text) > 50:
                formatted_text = self._format_long_text(key_text, 100)
                formatted_tooltip = self._format_tooltip(formatted_text, is_long_text=True)
                self.setToolTip(formatted_tooltip)
            # 否则检查文本是否被省略，显示完整文本
            elif self.text_label.is_text_elided():
                formatted_tooltip = self._format_tooltip(key_text)
                self.setToolTip(formatted_tooltip)
                
    def _format_tooltip(self, text: str, is_long_text: bool = False) -> str:
        """格式化tooltip文本，添加美化样式"""
        # 为tooltip添加HTML样式
        if is_long_text:
            return f'''<div style="
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, 
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                color: #495057;
                border: 1px solid #007bff;
                border-radius: 8px;
                padding: 12px 16px;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.4;
                max-width: 600px;
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.15);
                word-wrap: break-word;
            ">
                {text.replace(chr(10), '<br>')}
            </div>'''
        else:
            return f'''<div style="
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, 
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
                line-height: 1.3;
                max-width: 400px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                word-wrap: break-word;
            ">
                {text.replace(chr(10), '<br>')}
            </div>'''
                
    def _format_long_text(self, text: str, line_length: int = 100) -> str:
        """将长文本按指定长度换行格式化"""
        if len(text) <= line_length:
            return text
            
        lines = []
        start = 0
        while start < len(text):
            end = start + line_length
            if end >= len(text):
                lines.append(text[start:])
                break
            else:
                # 直接按字符长度换行
                lines.append(text[start:end])
                start = end
                
        return '\n'.join(lines)
            
    def update_button_text(self, new_text: str):
        self.send_button.setText(new_text)
        self.item_data["text"] = new_text
        
    def update_content_text(self, new_text: str):
        """更新文本内容"""
        self.text_label.setText(new_text)
        self.item_data["key"] = new_text
        # 更新发送函数
        self.send_button.clicked.disconnect()
        self.send_button.clicked.connect(lambda: self.send_requested.emit(new_text))


class QuickSendPanel(QDialog):
    """快捷发送面板对话框"""
    
    def __init__(self, parent=None, target_filename: str = ""):
        super().__init__(parent)
        self.target_filename = target_filename  # 指定要打开的文件
        self.data_files: List[str] = []
        self.current_data: List[Dict[str, Any]] = []
        self.all_data: Dict[str, List[Dict[str, Any]]] = {}
        self.filtered_data: List[Dict[str, Any]] = []
        
        # 在面板创建时先获取当前前台窗口，确保记录的是真正的目标窗口
        self._store_current_foreground_window()
        
        # 设置窗口标题
        if target_filename:
            self.setWindowTitle(f"快捷发送面板 - {target_filename}")
        else:
            self.setWindowTitle("快捷发送面板 - 快捷文本发送管理")
            
        self.setModal(True)
        self.resize(500, 600)  # 默认窗口大小为500x600
        self.setMinimumSize(400, 400)
        
        self._setup_ui()
        self._load_data_files()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部控制区域
        top_layout = QHBoxLayout()
        
        search_label = QLabel("搜索:")
        search_label.setFixedWidth(40)
        top_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        top_layout.addWidget(self.search_input)
        
        search_button = QPushButton("搜索")
        search_button.setFixedSize(60, 30)
        search_button.clicked.connect(self._perform_search)
        top_layout.addWidget(search_button)
        
        file_label = QLabel("文件:")
        file_label.setFixedWidth(35)
        top_layout.addWidget(file_label)
        
        self.file_combo = QComboBox()
        self.file_combo.setFixedWidth(150)
        self.file_combo.currentTextChanged.connect(self._on_file_changed)
        top_layout.addWidget(self.file_combo)
        
        layout.addLayout(top_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # 按钮显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.button_list = DraggableListWidget()
        self.button_list.item_moved.connect(self._on_item_moved)
        scroll_area.setWidget(self.button_list)
        layout.addWidget(scroll_area)
        
        # 底部添加区域
        add_layout = QHBoxLayout()
        content_label = QLabel("内容:")
        content_label.setFixedWidth(40)
        add_layout.addWidget(content_label)
        
        self.content_input = QLineEdit()
        self.content_input.setPlaceholderText("输入要发送的内容，如: 110, 密码123456")
        add_layout.addWidget(self.content_input)
        
        add_button = QPushButton("添加")
        add_button.setFixedSize(60, 30)
        add_button.clicked.connect(self._add_new_item)
        add_layout.addWidget(add_button)
        
        layout.addLayout(add_layout)
        
    def _load_data_files(self):
        data_dir = config_manager.config_dir / "quick_send"
        data_dir.mkdir(exist_ok=True)
        
        json_files = list(data_dir.glob("*.json"))
        if not json_files:
            self._create_sample_files(data_dir)
            json_files = list(data_dir.glob("*.json"))
            
        self.data_files = [f.stem for f in json_files]
        
        self.file_combo.clear()
        self.file_combo.addItem("全部文件", "all")
        for filename in self.data_files:
            self.file_combo.addItem(filename, filename)
            
        # 如果指定了目标文件，默认选中该文件
        if self.target_filename and self.target_filename in self.data_files:
            self.file_combo.setCurrentText(self.target_filename)
            
        self._load_all_data()
        self._update_display()
        
    def _create_sample_files(self, data_dir: Path):
        contacts_data = [
            {"key": "110", "text": "报警电话"},
            {"key": "120", "text": "急救电话"},
            {"key": "400-123-4567", "text": "客服电话"}
        ]
        
        passwords_data = [
            {"key": "123456", "text": "测试密码"},
            {"key": "admin", "text": "默认密码"}
        ]
        
        try:
            with open(data_dir / "常用联系方式.json", 'w', encoding='utf-8') as f:
                json.dump(contacts_data, f, indent=2, ensure_ascii=False)
            with open(data_dir / "常用密码.json", 'w', encoding='utf-8') as f:
                json.dump(passwords_data, f, indent=2, ensure_ascii=False)
            print("示例数据文件已创建")
        except Exception as e:
            print(f"创建示例文件失败: {e}")
            
    def _load_all_data(self):
        data_dir = config_manager.config_dir / "quick_send"
        self.all_data.clear()
        
        for filename in self.data_files:
            try:
                file_path = data_dir / f"{filename}.json"
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.all_data[filename] = data if isinstance(data, list) else []
            except Exception as e:
                print(f"加载文件失败 {filename}.json: {e}")
                self.all_data[filename] = []
                
    def _on_file_changed(self, text):
        self._update_display()
        
    def _update_display(self):
        selected_file = self.file_combo.currentData()
        
        if selected_file == "all":
            self.current_data = []
            for file_data in self.all_data.values():
                self.current_data.extend(file_data)
        else:
            self.current_data = self.all_data.get(selected_file, [])
            
        self._filter_data()
        
    def _filter_data(self):
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            self.filtered_data = self.current_data.copy()
        else:
            self.filtered_data = []
            for item in self.current_data:
                key = item.get("key", "").lower()
                text = item.get("text", "").lower()
                if search_text in key or search_text in text:
                    self.filtered_data.append(item)
                    
        self._refresh_list()
        
    def _refresh_list(self):
        self.button_list.clear()
        
        for index, item_data in enumerate(self.filtered_data):
            list_item = QListWidgetItem()
            
            button_widget = SendButtonWidget(item_data, index)
            button_widget.edit_requested.connect(self._edit_item)
            button_widget.delete_requested.connect(self._delete_item)
            button_widget.send_requested.connect(self._send_text)
            button_widget.content_changed.connect(self._auto_save_current_file)  # 连接内容变化信号
            
            list_item.setSizeHint(button_widget.sizeHint())
            self.button_list.addItem(list_item)
            self.button_list.setItemWidget(list_item, button_widget)
            
    def _on_search_text_changed(self, text):
        self._filter_data()
        
    def _perform_search(self):
        search_text = self.search_input.text().strip()
        if search_text:
            self.filtered_data = []
            search_lower = search_text.lower()
            
            for item in self.current_data:
                key = item.get("key", "").lower()
                text = item.get("text", "").lower()
                tooltip = item.get("tooltip", "").lower()
                
                if (search_lower in key or search_lower in text or search_lower in tooltip):
                    self.filtered_data.append(item)
                    
            self._refresh_list()
            
    def _send_text(self, text: str):
        """发送文本到上一个活动窗口并复制到剪贴板"""
        try:
            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # 直接粘贴到上一个活动窗口
            self._paste_to_previous_window()
            
            print(f"已粘贴文本: {text}")
            
        except Exception as e:
            QMessageBox.warning(self, "发送失败", f"发送文本失败: {e}")
            
    def _paste_to_previous_window(self):
        """切换到上一个窗口并执行粘贴"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_paste())
        
    def _switch_and_paste(self):
        """切换窗口并执行粘贴"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_paste())
        else:
            self._execute_paste()
            
    def _execute_paste(self):
        """执行粘贴操作"""
        try:
            import pyautogui
            # 使用Ctrl+V进行粘贴
            pyautogui.hotkey('ctrl', 'v')
        except ImportError:
            print("无法执行粘贴操作，仅复制到剪贴板")
        except Exception as e:
            print(f"粘贴失败: {e}")
        # 注意：不要在这里重新显示面板，保持目标窗口的焦点
            
    def _switch_to_previous_window(self) -> bool:
        """切换到上一个活动窗口"""
        # 获取浮动按钮的上一个活动窗口
        floating_button = self._get_floating_button()
        if not floating_button:
            return False
            
        last_window = getattr(floating_button, 'last_foreground_window', None)
        if not last_window:
            return False
            
        # Windows平台特定代码
        import sys
        if sys.platform == "win32":
            try:
                import win32gui
                import win32con
                
                # 检查窗口句柄是否仍然有效
                if win32gui.IsWindow(last_window):
                    # 如果被最小化则恢复
                    if win32gui.IsIconic(last_window):
                        win32gui.ShowWindow(last_window, win32con.SW_RESTORE)
                    # 设置为前台窗口
                    win32gui.SetForegroundWindow(last_window)
                    return True
            except Exception as e:
                print(f"切换窗口失败: {e}")
                
        return False
        
    def _get_floating_button(self):
        """获取浮动按钮实例"""
        # 向上查找父级窗口，直到找到FloatingButton
        parent = self.parent()
        while parent:
            if hasattr(parent, '__class__') and parent.__class__.__name__ == 'FloatingButton':
                return parent
            # 如果父级是ActionPanel，继续向上查找
            parent = parent.parent()
        return None
        
    def _store_current_foreground_window(self):
        """在面板创建时存储当前的前台窗口"""
        import sys
        if sys.platform == "win32":
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                
                # 检查是否是外部窗口（非应用内的对话框）
                window_title = win32gui.GetWindowText(hwnd)
                app_dialog_titles = [
                    "快捷发送面板",
                    "数据面板",
                    "编辑动作",
                    "新增动作",
                    "输入输出动作",
                    "脚本编辑器",
                    "图标选择",
                    "Quicker",
                    "关于"
                ]
                
                is_app_dialog = any(title in window_title for title in app_dialog_titles)
                
                if (win32gui.IsWindowVisible(hwnd) and 
                    window_title != "" and
                    not is_app_dialog):
                    # 直接设置浮动按钮的last_foreground_window
                    floating_button = self._get_floating_button()
                    if floating_button:
                        setattr(floating_button, 'last_foreground_window', hwnd)
                        print(f"[DEBUG] 在快捷发送面板创建时记录前台窗口: {window_title} (hwnd: {hwnd})")
                        
            except Exception as e:
                print(f"存储前台窗口失败: {e}")
        
    def _update_floating_button_last_window(self):
        """更新浮动按钮的前台窗口记录"""
        floating_button = self._get_floating_button()
        if floating_button:
            # 使用getattr安全调用方法
            update_method = getattr(floating_button, 'update_last_foreground_window', None)
            if update_method and callable(update_method):
                update_method()
            
    def _on_item_moved(self, from_index: int, to_index: int):
        if 0 <= from_index < len(self.filtered_data) and 0 <= to_index < len(self.filtered_data):
            item = self.filtered_data.pop(from_index)
            self.filtered_data.insert(to_index, item)
            
            selected_file = self.file_combo.currentData()
            if selected_file != "all" and selected_file in self.all_data:
                original_data = self.all_data[selected_file]
                if from_index < len(original_data) and to_index < len(original_data):
                    original_item = original_data.pop(from_index)
                    original_data.insert(to_index, original_item)
                    
                    # 自动保存
                    self._auto_save_current_file()
                    
    def _edit_item(self, index: int):
        if 0 <= index < len(self.filtered_data):
            item = self.filtered_data[index]
            
            current_text = item.get("text", "发送")
            new_text, ok = QInputDialog.getText(self, "编辑按钮文字", "按钮文字:", text=current_text)
            if ok and new_text.strip():
                item["text"] = new_text.strip()
                
                tooltip, ok2 = QInputDialog.getText(self, "编辑悬浮提示", "悬浮提示 (可选):", text=item.get("tooltip", ""))
                if ok2:
                    if tooltip.strip():
                        item["tooltip"] = tooltip.strip()
                    elif "tooltip" in item:
                        del item["tooltip"]
                
                # 自动保存
                self._auto_save_current_file()
                self._refresh_list()
                
    def _delete_item(self, index: int):
        if 0 <= index < len(self.filtered_data):
            reply = QMessageBox.question(
                self, "确认删除", 
                "确定要删除这个项目吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                item_to_delete = self.filtered_data[index]
                self.filtered_data.pop(index)
                
                for file_data in self.all_data.values():
                    if item_to_delete in file_data:
                        file_data.remove(item_to_delete)
                        break
                        
                # 自动保存
                self._auto_save_current_file()
                self._refresh_list()
                
    def _add_new_item(self):
        content = self.content_input.text().strip()
        
        if not content:
            QMessageBox.warning(self, "错误", "内容不能为空！")
            return
            
        new_item = {
            "key": content,
            "text": "发送"
        }
        
        selected_file = self.file_combo.currentData()
        
        # 如果有指定目标文件，优先添加到该文件
        if self.target_filename and self.target_filename in self.all_data:
            target_file = self.target_filename
        elif selected_file == "all":
            if self.data_files:
                target_file = self.data_files[0]
            else:
                QMessageBox.warning(self, "错误", "没有可用的文件！")
                return
        elif selected_file in self.all_data:
            target_file = selected_file
        else:
            QMessageBox.warning(self, "错误", "请选择一个有效的文件！")
            return
            
        self.all_data[target_file].append(new_item)
            
        # 自动保存
        self._auto_save_current_file()
        self.content_input.clear()
        self._update_display()
        
    def _create_new_file(self):
        filename, ok = QInputDialog.getText(self, "新建文件", "文件名:")
        if ok and filename.strip():
            filename = filename.strip()
            
            if filename in self.data_files:
                QMessageBox.warning(self, "错误", "文件已存在！")
                return
                
            try:
                data_dir = config_manager.config_dir / "quick_send"
                file_path = data_dir / f"{filename}.json"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                    
                self.data_files.append(filename)
                self.all_data[filename] = []
                
                self.file_combo.addItem(filename, filename)
                self.file_combo.setCurrentText(filename)
                
                QMessageBox.information(self, "成功", f"文件 {filename}.json 已创建！")
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件失败: {e}")
                
    def _save_current_file(self):
        selected_file = self.file_combo.currentData()
        
        if selected_file == "all":
            saved_count = 0
            for filename, data in self.all_data.items():
                if self._save_file_data(filename, data):
                    saved_count += 1
            QMessageBox.information(self, "保存完成", f"已保存 {saved_count} 个文件")
        elif selected_file in self.all_data:
            if self._save_file_data(selected_file, self.all_data[selected_file]):
                QMessageBox.information(self, "保存完成", f"文件 {selected_file}.json 已保存")
        else:
            QMessageBox.warning(self, "错误", "没有选中有效的文件！")
            
    def _save_file_data(self, filename: str, data: List[Dict[str, Any]]) -> bool:
        try:
            data_dir = config_manager.config_dir / "quick_send"
            file_path = data_dir / f"{filename}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存 {filename}.json 失败: {e}")
            return False
            
    def _auto_save_current_file(self):
        """自动保存当前文件"""
        selected_file = self.file_combo.currentData()
        
        # 如果有指定目标文件，优先保存该文件
        if self.target_filename and self.target_filename in self.all_data:
            self._save_file_data(self.target_filename, self.all_data[self.target_filename])
        elif selected_file == "all":
            # 保存所有文件
            for filename, data in self.all_data.items():
                self._save_file_data(filename, data)
        elif selected_file in self.all_data:
            self._save_file_data(selected_file, self.all_data[selected_file])
            
    def closeEvent(self, event):
        """关闭事件 - 自动保存并关闭，不弹出提示"""
        # 自动保存当前文件
        self._auto_save_current_file()
        # 直接关闭，不弹出提示
        event.accept()


# 为了向后兼容，保留原来的类名
DataPanelDialog = QuickSendPanel