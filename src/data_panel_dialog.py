# 快捷发送面板对话框模块 - 管理快捷发送文本和常用内容
import json
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QComboBox, QWidget, QMessageBox,
    QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag, QAction, QFont, QClipboard
from .config_manager import config_manager


class DraggableListWidget(QListWidget):
    """支持拖拽排序的列表控件"""
    
    item_moved = Signal(int, int)  # 发出移动信号 (from_index, to_index)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
    def dropEvent(self, event):
        """处理拖拽放下事件"""
        source_item = self.currentItem()
        if not source_item:
            return
            
        source_index = self.row(source_item)
        super().dropEvent(event)
        
        # 获取新位置
        target_index = self.row(source_item)
        if source_index != target_index:
            self.item_moved.emit(source_index, target_index)


class SendButtonWidget(QWidget):
    """发送按钮控件"""
    
    edit_requested = Signal(int)  # 编辑请求信号
    delete_requested = Signal(int)  # 删除请求信号
    send_requested = Signal(str)  # 发送请求信号
    
    def __init__(self, item_data: Dict[str, Any], index: int, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.index = index
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_tooltip)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 发送按钮（主要按钮）
        button_text = self.item_data.get("text", "发送")
        self.send_button = QPushButton(button_text)
        self.send_button.setMinimumHeight(40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        
        # 点击发送按钮时发送内容
        key_value = self.item_data.get("key", "")
        self.send_button.clicked.connect(lambda: self.send_requested.emit(key_value))
        
        layout.addWidget(self.send_button)
        
        # 设置整体样式
        self.setStyleSheet("""
            SendButtonWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 3px;
            }
            SendButtonWidget:hover {
                background-color: #e9ecef;
                border-color: #007bff;
            }
        """)
        
    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu(self)
        
        edit_action = QAction("编辑按钮文字", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.index))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.index))
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())
        
    def enterEvent(self, event):
        """鼠标进入事件"""
        super().enterEvent(event)
        # 只有在有提示内容时才显示
        if self.item_data.get("tooltip"):
            self.hover_timer.start(1000)  # 1秒后显示提示
        
    def leaveEvent(self, event):
        """鼠标离开事件"""
        super().leaveEvent(event)
        self.hover_timer.stop()
        
    def _show_tooltip(self):
        """显示悬浮提示"""
        tooltip_text = self.item_data.get("tooltip", "")
        if tooltip_text:
            self.setToolTip(tooltip_text)
            
    def update_button_text(self, new_text: str):
        """更新按钮文字"""
        self.send_button.setText(new_text)
        self.item_data["text"] = new_text


class DataPanelDialog(QDialog):
    """数据面板对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_files: List[str] = []  # JSON文件列表
        self.current_data: List[Dict[str, Any]] = []  # 当前显示的数据
        self.all_data: Dict[str, List[Dict[str, Any]]] = {}  # 所有文件的数据
        self.filtered_data: List[Dict[str, Any]] = []  # 筛选后的数据
        
        self.setWindowTitle("数据面板 - 快捷键和常用文本管理")
        self.setModal(True)
        self.resize(700, 600)
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_data_files()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部控制区域
        top_layout = QHBoxLayout()
        
        # 搜索框
        search_label = QLabel("搜索:")
        search_label.setFixedWidth(40)
        top_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        top_layout.addWidget(self.search_input)
        
        # 搜索按钮
        search_button = QPushButton("搜索")
        search_button.setFixedSize(60, 30)
        search_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        search_button.clicked.connect(self._perform_search)
        top_layout.addWidget(search_button)
        
        # 文件选择下拉框
        file_label = QLabel("文件:")
        file_label.setFixedWidth(35)
        top_layout.addWidget(file_label)
        
        self.file_combo = QComboBox()
        self.file_combo.setFixedWidth(200)
        self.file_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                min-width: 150px;
            }
        """)
        self.file_combo.currentTextChanged.connect(self._on_file_changed)
        top_layout.addWidget(self.file_combo)
        
        layout.addLayout(top_layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #ddd; }")
        layout.addWidget(separator)
        
        # 数据显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
        """)
        
        self.data_list = DraggableListWidget()
        self.data_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                border: none;
                margin: 2px;
                padding: 0px;
            }
        """)
        self.data_list.item_moved.connect(self._on_item_moved)
        
        scroll_area.setWidget(self.data_list)
        layout.addWidget(scroll_area)
        
        # 底部添加区域
        bottom_layout = QVBoxLayout()
        
        # 添加输入区域
        add_layout = QHBoxLayout()
        
        key_label = QLabel("键名:")
        key_label.setFixedWidth(40)
        add_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("如: 110, 密码")
        self.key_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        add_layout.addWidget(self.key_input)
        
        value_label = QLabel("值:")
        value_label.setFixedWidth(30)
        add_layout.addWidget(value_label)
        
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("如: 报警号码, 测试常用密码")
        self.value_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        add_layout.addWidget(self.value_input)
        
        add_button = QPushButton("添加")
        add_button.setFixedSize(60, 30)
        add_button.setStyleSheet("""
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
        """)
        add_button.clicked.connect(self._add_new_item)
        add_layout.addWidget(add_button)
        
        bottom_layout.addLayout(add_layout)
        
        # 文件管理按钮
        file_mgmt_layout = QHBoxLayout()
        file_mgmt_layout.addStretch()
        
        new_file_button = QPushButton("新建文件")
        new_file_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_file_button.clicked.connect(self._create_new_file)
        file_mgmt_layout.addWidget(new_file_button)
        
        save_button = QPushButton("保存当前")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        save_button.clicked.connect(self._save_current_file)
        file_mgmt_layout.addWidget(save_button)
        
        bottom_layout.addLayout(file_mgmt_layout)
        layout.addWidget(QWidget())  # 占位符
        layout.addLayout(bottom_layout)
        
        # 关闭按钮
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        close_button = QPushButton("关闭")
        close_button.setFixedSize(80, 35)
        close_button.setStyleSheet("""
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
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)
        
        layout.addLayout(close_layout)
        
    def _load_data_files(self):
        """加载数据文件列表"""
        # 创建数据目录
        data_dir = config_manager.config_dir / "data_panels"
        data_dir.mkdir(exist_ok=True)
        
        # 查找所有JSON文件
        json_files = list(data_dir.glob("*.json"))
        
        # 如果没有文件，创建示例文件
        if not json_files:
            self._create_sample_files(data_dir)
            json_files = list(data_dir.glob("*.json"))
            
        self.data_files = [f.stem for f in json_files]
        
        # 更新下拉框
        self.file_combo.clear()
        self.file_combo.addItem("全部文件", "all")
        for filename in self.data_files:
            self.file_combo.addItem(filename, filename)
            
        # 加载所有文件数据
        self._load_all_data()
        
        # 默认显示全部
        self._update_display()
        
    def _create_sample_files(self, data_dir: Path):
        """创建示例文件"""
        # 示例文件1: 常用联系方式
        contacts_data = [
            {"key": "110", "value": "报警电话", "tooltip": "{110}{报警电话}"},
            {"key": "120", "value": "急救电话", "tooltip": "{120}{急救电话}"},
            {"key": "119", "value": "火警电话", "tooltip": "{119}{火警电话}"},
            {"key": "客服", "value": "400-123-4567", "tooltip": "{客服}{400-123-4567}"}
        ]
        
        # 示例文件2: 常用密码
        passwords_data = [
            {"key": "测试密码", "value": "123456", "tooltip": "{测试密码}{123456}"},
            {"key": "默认密码", "value": "admin", "tooltip": "{默认密码}{admin}"},
            {"key": "安全密码", "value": "P@ssw0rd", "tooltip": "{安全密码}{P@ssw0rd}"}
        ]
        
        # 保存示例文件
        try:
            with open(data_dir / "常用联系方式.json", 'w', encoding='utf-8') as f:
                json.dump(contacts_data, f, indent=2, ensure_ascii=False)
                
            with open(data_dir / "常用密码.json", 'w', encoding='utf-8') as f:
                json.dump(passwords_data, f, indent=2, ensure_ascii=False)
                
            print("示例数据文件已创建")
        except Exception as e:
            print(f"创建示例文件失败: {e}")
            
    def _load_all_data(self):
        """加载所有文件数据"""
        data_dir = config_manager.config_dir / "data_panels"
        self.all_data.clear()
        
        for filename in self.data_files:
            try:
                file_path = data_dir / f"{filename}.json"
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.all_data[filename] = data
                    else:
                        print(f"文件格式错误: {filename}.json")
                        self.all_data[filename] = []
            except Exception as e:
                print(f"加载文件失败 {filename}.json: {e}")
                self.all_data[filename] = []
                
    def _on_file_changed(self, text):
        """文件选择改变"""
        self._update_display()
        
    def _update_display(self):
        """更新显示内容"""
        selected_file = self.file_combo.currentData()
        
        if selected_file == "all":
            # 显示所有文件的数据
            self.current_data = []
            for file_data in self.all_data.values():
                self.current_data.extend(file_data)
        else:
            # 显示选中文件的数据
            self.current_data = self.all_data.get(selected_file, [])
            
        # 应用搜索筛选
        self._filter_data()
        
    def _filter_data(self):
        """筛选数据"""
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            self.filtered_data = self.current_data.copy()
        else:
            self.filtered_data = []
            for item in self.current_data:
                key = item.get("key", "").lower()
                value = item.get("value", "").lower()
                if search_text in key or search_text in value:
                    self.filtered_data.append(item)
                    
        self._refresh_list()
        
    def _refresh_list(self):
        """刷新列表显示"""
        self.data_list.clear()
        
        for index, item_data in enumerate(self.filtered_data):
            list_item = QListWidgetItem()
            
            item_widget = DataItemWidget(item_data, index)
            item_widget.edit_requested.connect(self._edit_item)
            item_widget.delete_requested.connect(self._delete_item)
            
            list_item.setSizeHint(item_widget.sizeHint())
            self.data_list.addItem(list_item)
            self.data_list.setItemWidget(list_item, item_widget)
            
    def _on_search_text_changed(self, text):
        """搜索文本变化"""
        self._filter_data()
        
    def _perform_search(self):
        """执行模糊搜索"""
        # 这里可以实现更复杂的模糊搜索逻辑
        search_text = self.search_input.text().strip()
        if search_text:
            # 扩展搜索范围，包括提示文本
            self.filtered_data = []
            search_lower = search_text.lower()
            
            for item in self.current_data:
                key = item.get("key", "").lower()
                value = item.get("value", "").lower()
                tooltip = item.get("tooltip", "").lower()
                
                if (search_lower in key or 
                    search_lower in value or 
                    search_lower in tooltip):
                    self.filtered_data.append(item)
                    
            self._refresh_list()
            
    def _on_item_moved(self, from_index: int, to_index: int):
        """处理项目移动"""
        if 0 <= from_index < len(self.filtered_data) and 0 <= to_index < len(self.filtered_data):
            # 在筛选数据中移动
            item = self.filtered_data.pop(from_index)
            self.filtered_data.insert(to_index, item)
            
            # 同步到原始数据（如果显示单个文件）
            selected_file = self.file_combo.currentData()
            if selected_file != "all" and selected_file in self.all_data:
                # 找到对应的原始索引并移动
                original_data = self.all_data[selected_file]
                if from_index < len(original_data) and to_index < len(original_data):
                    original_item = original_data.pop(from_index)
                    original_data.insert(to_index, original_item)
                    
    def _edit_item(self, index: int):
        """编辑项目"""
        if 0 <= index < len(self.filtered_data):
            item = self.filtered_data[index]
            
            # 创建编辑对话框
            key, ok1 = QInputDialog.getText(self, "编辑键名", "键名:", text=item.get("key", ""))
            if not ok1:
                return
                
            value, ok2 = QInputDialog.getText(self, "编辑值", "值:", text=item.get("value", ""))
            if not ok2:
                return
                
            # 更新数据
            item["key"] = key.strip()
            item["value"] = value.strip()
            item["tooltip"] = f"{{{key}}}{{{value}}}"
            
            self._refresh_list()
            
    def _delete_item(self, index: int):
        """删除项目"""
        if 0 <= index < len(self.filtered_data):
            reply = QMessageBox.question(
                self, "确认删除", 
                "确定要删除这个项目吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                item_to_delete = self.filtered_data[index]
                
                # 从筛选数据中删除
                self.filtered_data.pop(index)
                
                # 从原始数据中删除
                for file_data in self.all_data.values():
                    if item_to_delete in file_data:
                        file_data.remove(item_to_delete)
                        break
                        
                self._refresh_list()
                
    def _add_new_item(self):
        """添加新项目"""
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        
        if not key or not value:
            QMessageBox.warning(self, "错误", "键名和值都不能为空！")
            return
            
        # 创建新项目
        new_item = {
            "key": key,
            "value": value,
            "tooltip": f"{{{key}}}{{{value}}}"
        }
        
        # 添加到当前选中的文件
        selected_file = self.file_combo.currentData()
        if selected_file == "all":
            # 如果选择全部，添加到第一个文件
            if self.data_files:
                first_file = self.data_files[0]
                self.all_data[first_file].append(new_item)
        elif selected_file in self.all_data:
            self.all_data[selected_file].append(new_item)
        else:
            QMessageBox.warning(self, "错误", "请选择一个有效的文件！")
            return
            
        # 清空输入框
        self.key_input.clear()
        self.value_input.clear()
        
        # 刷新显示
        self._update_display()
        
    def _create_new_file(self):
        """创建新文件"""
        filename, ok = QInputDialog.getText(self, "新建文件", "文件名:")
        if ok and filename.strip():
            filename = filename.strip()
            
            # 检查文件是否已存在
            if filename in self.data_files:
                QMessageBox.warning(self, "错误", "文件已存在！")
                return
                
            # 创建新文件
            try:
                data_dir = config_manager.config_dir / "data_panels"
                file_path = data_dir / f"{filename}.json"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                    
                # 更新数据
                self.data_files.append(filename)
                self.all_data[filename] = []
                
                # 更新下拉框
                self.file_combo.addItem(filename, filename)
                self.file_combo.setCurrentText(filename)
                
                QMessageBox.information(self, "成功", f"文件 {filename}.json 已创建！")
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件失败: {e}")
                
    def _save_current_file(self):
        """保存当前文件"""
        selected_file = self.file_combo.currentData()
        
        if selected_file == "all":
            # 保存所有文件
            saved_count = 0
            for filename, data in self.all_data.items():
                if self._save_file_data(filename, data):
                    saved_count += 1
            QMessageBox.information(self, "保存完成", f"已保存 {saved_count} 个文件")
        elif selected_file in self.all_data:
            # 保存选中文件
            if self._save_file_data(selected_file, self.all_data[selected_file]):
                QMessageBox.information(self, "保存完成", f"文件 {selected_file}.json 已保存")
        else:
            QMessageBox.warning(self, "错误", "没有选中有效的文件！")
            
    def _save_file_data(self, filename: str, data: List[Dict[str, Any]]) -> bool:
        """保存文件数据"""
        try:
            data_dir = config_manager.config_dir / "data_panels"
            file_path = data_dir / f"{filename}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存 {filename}.json 失败: {e}")
            return False
            
    def closeEvent(self, event):
        """关闭事件"""
        # 询问是否保存
        reply = QMessageBox.question(
            self, "确认关闭", 
            "是否保存当前更改？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._save_current_file()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            event.accept()
        else:
            event.ignore()