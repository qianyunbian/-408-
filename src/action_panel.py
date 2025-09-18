# 动作面板模块
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, 
    QMenu, QInputDialog, QMessageBox, QDialog, QTextEdit,
    QListWidget, QListWidgetItem, QHBoxLayout, QComboBox, QPlainTextEdit, QLineEdit,
    QTabWidget
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QCursor
from .config_manager import config_manager
import uuid
import copy

if TYPE_CHECKING:
    from .floating_button import FloatingButton
    from .button_widget import DraggableButton

class SilentInfoDialog(QDialog):
    """无声信息对话框（不播放系统提示音）"""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        
        # 设置窗口标志，移除问号按钮
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # 布局
        layout = QVBoxLayout(self)
        
        # 文本显示区域（只读）
        text_edit = QTextEdit()
        text_edit.setPlainText(message)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(text_edit)
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        ok_button.clicked.connect(self.accept)
        
        # 按钮布局
        button_layout = QVBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(button_layout)


class BackupSelectionDialog(QDialog):
    """备份文件选择对话框"""
    def __init__(self, backup_files: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.backup_files = backup_files
        self.selected_backup = None
        
        self.setWindowTitle("选择备份文件")
        self.setModal(True)
        self.setFixedSize(600, 400)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("请选择要载入的备份文件：")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 备份文件列表
        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
                background-color: white;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
                font-weight: bold;
            }
            QListWidget::item:selected:hover {
                background-color: #0056b3;
                color: white;
            }
        """)
        
        # 按时间排序（最新的在前）
        sorted_files = sorted(self.backup_files, key=lambda x: x['modified'], reverse=True)
        
        for file_info in sorted_files:
            # 格式化显示文本，使用更清晰的布局
            filename = file_info['name']
            size_kb = file_info['size_kb']
            modified_time = file_info['modified']
            
            # 提取时间戳信息使其更易读
            try:
                # 从文件名中提取时间信息
                time_part = filename.replace('config_backup_', '').replace('.json', '')
                if '_' in time_part:
                    date_part, time_part = time_part.split('_')
                    formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                    formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
                    display_time = f"{formatted_date} {formatted_time}"
                else:
                    display_time = modified_time
            except:
                display_time = modified_time
                
            item_text = f"{display_time}\n文件: {filename}  |  大小: {size_kb} KB"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, file_info['name'])  # 存储文件名
            self.backup_list.addItem(item)
        
        # 双击选中事件
        self.backup_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.backup_list)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("取消")
        cancel_button.setFixedSize(80, 30)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        self.ok_button = QPushButton("载入")
        self.ok_button.setFixedSize(80, 30)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # 监听选中变化
        self.backup_list.itemSelectionChanged.connect(self._on_selection_changed)
        
    def _on_selection_changed(self):
        """选中变化事件"""
        current_item = self.backup_list.currentItem()
        self.ok_button.setEnabled(current_item is not None)
        
    def _on_item_double_clicked(self, item):
        """双击事件"""
        self.selected_backup = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        
    def _on_ok_clicked(self):
        """确认按钮事件"""
        current_item = self.backup_list.currentItem()
        if current_item:
            self.selected_backup = current_item.data(Qt.ItemDataRole.UserRole)
            self.accept()
            
    def get_selected_backup(self) -> Optional[str]:
        """获取选中的备份文件名"""
        return self.selected_backup


class InputOutputActionDialog(QDialog):
    """输入输出动作创建对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_data = None
        
        self.setWindowTitle("创建输入输出动作")
        self.setModal(True)
        self.setFixedSize(800, 650)
        
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


class ActionPanel(QWidget):
    
    # 类变量
    _panel_states: Dict[str, Dict[str, Any]] = {}
    _open_panels: List['ActionPanel'] = []
    
    # 全局剪贴板系统
    _clipboard_action: Optional[Dict[str, Any]] = None
    _clipboard_operation: str = ""  # "copy" 或 "cut"
    _clipboard_source_panel: Optional['ActionPanel'] = None
    
    def __init__(self, parent=None, actions: Optional[List[Dict[str, Any]]] = None, level: int = 0):
        super().__init__(parent)
        
        self.level = level
        self.action_configs = actions if actions is not None else config_manager.get("actions", [])
        self.parent_panel = parent if isinstance(parent, ActionPanel) else None
        self.sub_panels: List['ActionPanel'] = []
        self.buttons: List[DraggableButton] = []
        self._dragged_button: Optional[DraggableButton] = None
        self._current_placeholder_index = -1
        
        # 生成面板ID
        self._panel_id = self._generate_panel_id()
        
        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.setup_ui()
        self.load_actions()
        
        # 启用拖放
        self.setAcceptDrops(True)
        
        # 将面板添加到跟踪列表中（模仿1.94.py方式）
        if self not in ActionPanel._open_panels:
            ActionPanel._open_panels.append(self)
            print(f"[DEBUG] 新面板已添加到跟踪列表: {self._panel_id}")
            
    def showEvent(self, event):
        """面板显示事件（模仿1.94.py方式）"""
        super().showEvent(event)
        # 确保显示的面板在跟踪列表中
        if self not in ActionPanel._open_panels:
            ActionPanel._open_panels.append(self)
            print(f"[DEBUG] 面板显示时添加到跟踪列表: {self._panel_id}")
            
    def hideEvent(self, event):
        """面板隐藏事件（模仿1.94.py方式）"""
        super().hideEvent(event)
        # 当面板隐藏时，从跟踪列表中移除（但不删除主面板）
        if self in ActionPanel._open_panels and self._panel_id != "main_panel":
            ActionPanel._open_panels.remove(self)
            print(f"[DEBUG] 面板隐藏时从跟踪列表移除: {self._panel_id}")
            
    def closeEvent(self, event):
        """面板关闭事件（模仿1.94.py方式）"""
        # 从跟踪列表中移除
        if self in ActionPanel._open_panels:
            ActionPanel._open_panels.remove(self)
            print(f"[DEBUG] 面板关闭时从跟踪列表移除: {self._panel_id}")
        super().closeEvent(event)
        
    def _generate_panel_id(self) -> str:
        """生成面板唯一标识符"""
        parent = self.parent()
        
        # 检查是否是主面板
        if hasattr(parent, '__class__') and parent.__class__.__name__ == 'FloatingButton':
            return "main_panel"
        elif isinstance(parent, ActionPanel):
            parent_id = getattr(parent, '_panel_id', 'unknown')
            try:
                index = parent.sub_panels.index(self) if hasattr(parent, 'sub_panels') else 0
            except (ValueError, AttributeError):
                index = len(getattr(parent, 'sub_panels', []))
            return f"{parent_id}_sub_{index}"
        else:
            return f"panel_{uuid.uuid4().hex[:8]}"
    
    def setup_ui(self):
        """设置用户界面"""
        panel_config = config_manager.get("action_panel", {})
        btn_config = config_manager.get("action_buttons", {})
        
        # 设置面板样式（只对ActionPanel生效，不影响子组件）
        self.setStyleSheet(f"""
            ActionPanel {{
                background-color: {panel_config.get("background_color", "rgba(240, 240, 240, 0.95)")};
                border-radius: 10px;
                border: 1px solid #ccc;
            }}
        """)
        
        # 计算面板尺寸
        btn_size = btn_config.get("size", 80)
        columns = panel_config.get("columns", 4)
        spacing = btn_config.get("spacing", 10)
        
        panel_width = columns * btn_size + (columns - 1) * spacing + 20
        panel_height = max(300, panel_width * 1.2)
        
        self.setFixedSize(
            panel_config.get("width", panel_width), 
            panel_config.get("height", panel_height)
        )
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title_label = QLabel("Quicker")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #333; "
            "border: none; background: transparent;"
        )
        main_layout.addWidget(title_label)
        
        # 网格布局
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(btn_config.get("spacing", 10))
        main_layout.addLayout(self.grid_layout)
        
        # 返回按钮（如果不是主面板）
        if self.level > 0:
            back_button = QPushButton("返回")
            back_button.clicked.connect(self.go_back)
            main_layout.addWidget(back_button)
        
        main_layout.addStretch()
        
        # 占位符控件
        btn_size = btn_config.get("size", 80)
        self.drop_placeholder = QWidget()
        self.drop_placeholder.setFixedSize(btn_size, btn_size)
        self.drop_placeholder.setStyleSheet(
            "background-color: transparent; border: 2px dashed #999; border-radius: 8px;"
        )
        
    def load_actions(self):
        """刷新动作按钮界面（重新创建所有按钮和布局）"""
        # 清除现有按钮
        for button in self.buttons:
            button.deleteLater()
        self.buttons.clear()
        self.sub_panels.clear()
        
        # 创建动作按钮
        for action_config in self.action_configs:
            from .button_widget import DraggableButton
            button = DraggableButton(action_config, self)
            
            # 连接信号
            button.rename_requested.connect(self.handle_rename_action)
            button.icon_change_requested.connect(self.handle_icon_change)
            button.delete_requested.connect(lambda btn=button: self.handle_delete_action(btn))
            button.copy_requested.connect(lambda btn=button: self.handle_copy_action(btn))
            button.cut_requested.connect(lambda btn=button: self.handle_cut_action(btn))
            button.edit_requested.connect(lambda btn=button: self.handle_edit_action(btn))
            
            # 根据动作类型连接点击事件
            action_type = action_config.get("type")
            if action_type == "key":
                cmd = action_config.get("command", "")
                button.clicked.connect(lambda c=cmd: self.simulate_key(c))
            elif action_type == "program":
                cmd = action_config.get("command", "")
                button.clicked.connect(lambda c=cmd: self.run_program(c))
            elif action_type == "url":
                url = action_config.get("url", "")
                button.clicked.connect(lambda u=url: self.open_url(u))
            elif action_type == "text":
                txt = action_config.get("text", "")
                button.clicked.connect(lambda t=txt: self.send_text(t))
            elif action_type == "panel":
                acts = action_config.get("actions", [])
                button.clicked.connect(lambda a=acts: self.open_sub_panel(a))
            elif action_type == "input_output":
                script_file = action_config.get("script_file", "")
                input_source = action_config.get("input_source", "clipboard")
                output_target = action_config.get("output_target", "text")
                button.clicked.connect(lambda sf=script_file, ins=input_source, out=output_target: 
                                     self.execute_input_output(sf, ins, out))
            elif action_type == "quick_send":
                # 快捷发送动作 - 打开快捷发送面板
                filename = action_config.get("filename", "")
                button.clicked.connect(lambda f=filename: self.open_quick_send_panel(f))
            
            self.buttons.append(button)
        
        self._relayout_buttons()
        
    def _relayout_buttons(self):
        """重新布局按钮"""
        # 清除现有布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        columns = config_manager.get("action_panel.columns", 4)
        
        # 放置动作按钮
        for i, button in enumerate(self.buttons):
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(button, row, col)
        
        # 添加空白占位符
        num_buttons = len(self.buttons)
        if columns > 0 and num_buttons % columns != 0:
            placeholders_to_add = columns - (num_buttons % columns)
            start_index = num_buttons
            btn_size = config_manager.get("action_buttons.size", 66)  # 修改默认大小为66
            
            for i in range(placeholders_to_add):
                placeholder = QWidget()
                placeholder.setFixedSize(btn_size, btn_size)
                placeholder.setStyleSheet(
                    "background-color: transparent; border: 1px dashed #ccc; border-radius: 8px;"
                )
                
                current_index = start_index + i
                row = current_index // columns
                col = current_index % columns
                self.grid_layout.addWidget(placeholder, row, col)
        
        # 添加"新增动作"按钮
        self._add_control_buttons(columns)
        
    def _add_control_buttons(self, columns: int):
        """添加控制按钮（新增、设置等）"""
        btn_size = config_manager.get("action_buttons.size", 66)  # 修改默认大小为66
        
        # 新增动作按钮
        add_btn = QPushButton("+")
        add_btn.setFixedSize(btn_size, btn_size)
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 36px;
                color: #4f7cff;
                border: 2px solid #4f7cff;
                background: #f8fbff;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #e6f0ff;
                color: #2a5cff;
            }
        """)
        add_btn.setToolTip("新增动作")
        add_btn.clicked.connect(self.add_new_action)
        
        row = len(self.buttons) // columns
        col = len(self.buttons) % columns
        self.grid_layout.addWidget(add_btn, row, col)
        
        # 配置管理按钮
        config_btn = QPushButton("⚙")
        config_btn.setFixedSize(btn_size, btn_size)
        config_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                color: #4f7cff;
                border: 2px solid #4f7cff;
                background: #f8fbff;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #e6f0ff;
                color: #2a5cff;
                border-color: #4f7cff;
            }
        """)
        config_btn.setToolTip("配置管理")
        config_btn.clicked.connect(self.show_config_menu)
        
        row = (len(self.buttons) + 1) // columns
        col = (len(self.buttons) + 1) % columns
        self.grid_layout.addWidget(config_btn, row, col)
        
    def add_new_action(self):
        """添加新动作"""
        menu = QMenu(self)
        menu.addAction("模拟按键", lambda: self.create_new_action("key"))
        menu.addAction("运行程序", lambda: self.create_new_action("program"))
        menu.addAction("打开网址", lambda: self.create_new_action("url"))
        menu.addAction("发送文本", lambda: self.create_new_action("text"))
        menu.addAction("输入输出", lambda: self.create_new_action("input_output"))
        menu.addAction("快捷发送", lambda: self.create_new_action("quick_send"))
        menu.addAction("新建子页面", lambda: self.create_new_action("panel"))
        menu.exec(QCursor.pos())
        
    def create_new_action(self, action_type: str):
        """创建新动作"""
        action = None
        
        if action_type == "key":
            text, ok = QInputDialog.getText(
                self, "新增动作", 
                "请输入要模拟的按键序列：\\n\\n"
                "支持格式：\\n"
                "• 组合键: ctrl+c, alt+tab\\n"
                "• 单个按键: f5, enter, space\\n"
                "• 文本串: \"hello world\"\\n"
                "• 延时等待: wait(1000)\\n"
                "• 序列组合: ctrl+c, wait(500), \"text\", enter"
            )
            if ok and text.strip():
                action = config_manager.create_action("模拟按键", "key", command=text.strip())
                
        elif action_type == "program":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入程序路径或文件路径：")
            if ok and text.strip():
                action = config_manager.create_action("运行程序", "program", command=text.strip())
                
        elif action_type == "url":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入网址（URL）：")
            if ok and text.strip():
                action = config_manager.create_action("打开网址", "url", url=text.strip())
                
        elif action_type == "text":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入要发送的文本内容：")
            if ok and text.strip():
                action = config_manager.create_action("发送文本", "text", text=text.strip())
                
        elif action_type == "panel":
            text, ok = QInputDialog.getText(self, "新增子页面", "请输入子页面名称：")
            if ok and text.strip():
                action = config_manager.create_action(text.strip(), "panel", actions=[])
                
        elif action_type == "input_output":
            # 创建输入输出动作
            from .input_output_dialog import InputOutputActionDialog
            dialog = InputOutputActionDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                action_data = dialog.get_action_data()
                if action_data:
                    action = action_data
                    
        elif action_type == "quick_send":
            # 创建快捷发送动作
            name, ok = QInputDialog.getText(self, "新建快捷发送", "请输入快捷发送动作名称：")
            if ok and name.strip():
                import datetime
                import uuid
                import re
                
                # 清理用户输入的名称，生成合法的文件名
                clean_name = name.strip()
                # 移除非法字符，只保留中文、英文、数字、下划线和短横线
                safe_filename = re.sub(r'[^\w\u4e00-\u9fff-]', '_', clean_name)
                # 确保文件名不为空
                if not safe_filename:
                    safe_filename = f"quick_send_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 检查文件名是否已存在，如果存在则添加序号
                data_dir = config_manager.config_dir / "quick_send"
                data_dir.mkdir(exist_ok=True)
                
                original_filename = safe_filename
                counter = 1
                while (data_dir / f"{safe_filename}.json").exists():
                    safe_filename = f"{original_filename}_{counter}"
                    counter += 1
                
                file_path = data_dir / f"{safe_filename}.json"
                
                try:
                    import json
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump([], f, indent=2, ensure_ascii=False)
                    
                    # 创建动作配置，文件名就是清理后的用户名称
                    action = config_manager.create_action(
                        clean_name, 
                        "quick_send", 
                        filename=safe_filename,
                        description=f"快捷发送: {clean_name}"
                    )
                    
                    print(f"已创建快捷发送动作: {clean_name}, 文件: {safe_filename}.json")
                    
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"创建文件失败: {e}")
                    return
        
        if action:
            # 添加到当前面板
            self.action_configs.append(action)
            self.save_config()  # 标记配置变化，但不立即保存
            self.load_actions()
        
    def handle_rename_action(self, action_id: str):
        """处理重命名动作"""
        self.save_config()  # 标记配置变化
        
    def handle_icon_change(self, action_id: str):
        """处理图标更改"""
        self.save_config()  # 标记配置变化
        
    def handle_delete_action(self, button):
        """处理删除动作"""
        try:
            index = self.buttons.index(button)
            del self.action_configs[index]
            self.save_config()  # 标记配置变化
            self.load_actions()
        except (ValueError, IndexError):
            pass
            
    def handle_copy_action(self, button):
        """处理复制动作"""
        try:
            index = self.buttons.index(button)
            action_to_copy = copy.deepcopy(self.action_configs[index])
            
            # 更新全局剪贴板
            ActionPanel._clipboard_action = action_to_copy
            ActionPanel._clipboard_operation = "copy"
            ActionPanel._clipboard_source_panel = self
            
            print(f"[复制] 动作 '{action_to_copy.get('name', '')}' 已复制到剪贴板")
            
        except (ValueError, IndexError):
            pass
            
    def handle_cut_action(self, button):
        """处理剪切动作"""
        try:
            index = self.buttons.index(button)
            action_to_cut = copy.deepcopy(self.action_configs[index])
            
            # 更新全局剪贴板
            ActionPanel._clipboard_action = action_to_cut
            ActionPanel._clipboard_operation = "cut"
            ActionPanel._clipboard_source_panel = self
            
            print(f"[剪切] 动作 '{action_to_cut.get('name', '')}' 已剪切到剪贴板")
            
            # 剪切后立即从当前面板删除
            del self.action_configs[index]
            self.save_config()  # 标记配置变化
            self.load_actions()
            
        except (ValueError, IndexError):
            pass
            
    def handle_edit_action(self, button):
        """处理编辑动作"""
        try:
            index = self.buttons.index(button)
            action_config = self.action_configs[index]
            
            # 创建编辑对话框
            from .action_edit_dialog import ActionEditDialog
            dialog = ActionEditDialog(action_config, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 更新配置
                updated_config = dialog.get_updated_config()
                self.action_configs[index] = updated_config
                
                # 保存配置并刷新界面
                self.save_config()  # 标记配置变化
                self.load_actions()
                
                print(f"[编辑] 动作 '{updated_config.get('name', '')}' 已更新")
                
        except (ValueError, IndexError, Exception) as e:
            print(f"[编辑] 编辑动作失败: {e}")
            QMessageBox.warning(self, "错误", f"编辑动作失败: {e}")
            
    def paste_action(self):
        """粘贴动作"""
        if not ActionPanel._clipboard_action:
            QMessageBox.information(self, "提示", "剪贴板为空，没有可粘贴的动作")
            return
            
        # 创建动作副本（生成新ID）
        new_action = copy.deepcopy(ActionPanel._clipboard_action)
        new_action["id"] = str(uuid.uuid4())  # 生成新的唯一ID
        
        # 如果是剪切操作，检查是否是粘贴到同一个面板
        if (ActionPanel._clipboard_operation == "cut" and 
            ActionPanel._clipboard_source_panel == self):
            # 在同一个面板内剪切粘贴，不做处理
            QMessageBox.information(self, "提示", "不能在同一个面板内剪切粘贴")
            return
            
        # 添加到当前面板
        self.action_configs.append(new_action)
        self.save_config()  # 标记配置变化
        self.load_actions()
        
        operation_name = "剪切" if ActionPanel._clipboard_operation == "cut" else "复制"
        action_name = new_action.get('name', '未知动作')
        print(f"[粘贴] 从{operation_name}粘贴动作 '{action_name}' 到当前面板")
        
        # 如果是剪切操作，清空剪贴板（防止重复粘贴）
        if ActionPanel._clipboard_operation == "cut":
            ActionPanel._clipboard_action = None
            ActionPanel._clipboard_operation = ""
            ActionPanel._clipboard_source_panel = None
            print("[粘贴] 剪切操作完成，已清空剪贴板")
            
    def handle_button_drop(self, button, position: QPoint):
        """处理按钮拖放"""
        target_index = self.get_grid_index(position)
        
        try:
            source_index = self.buttons.index(button)
            if 0 <= target_index < len(self.buttons) and target_index != source_index:
                # 交换按钮和动作
                (self.buttons[source_index], self.buttons[target_index]) = (
                    self.buttons[target_index], self.buttons[source_index]
                )
                (self.action_configs[source_index], self.action_configs[target_index]) = (
                    self.action_configs[target_index], self.action_configs[source_index]
                )
                
                self._relayout_buttons()
                self.save_config()  # 标记配置变化
        except (ValueError, IndexError):
            pass
            
        # 清理拖拽状态
        self._dragged_button = None
        
    def get_grid_index(self, pos: QPoint) -> int:
        """获取网格索引"""
        layout_rect = self.grid_layout.geometry()
        if not layout_rect.contains(pos):
            pos.setX(max(layout_rect.left(), min(pos.x(), layout_rect.right())))
            pos.setY(max(layout_rect.top(), min(pos.y(), layout_rect.bottom())))

        relative_pos = pos - layout_rect.topLeft()
        
        btn_config = config_manager.get("action_buttons", {})
        cell_width = btn_config.get("size", 66) + self.grid_layout.spacing()
        cell_height = btn_config.get("size", 66) + self.grid_layout.spacing()

        if cell_width <= 0 or cell_height <= 0:
            return 0

        row = relative_pos.y() // cell_height
        col = relative_pos.x() // cell_width
        
        columns = config_manager.get("action_panel.columns", 4)
        row = max(0, row)
        col = max(0, min(col, columns - 1))
        
        index = row * columns + col
        return min(index, len(self.buttons))
        
    def open_sub_panel(self, actions: List[Dict[str, Any]]):
        """打开子面板（模仿1.94.py方式）"""
        if self.level >= 4:  # 最大5层
            QMessageBox.warning(self, "提示", "已达到最大层级。")
            return
            
        # 创建子面板
        sub_panel = ActionPanel(parent=self, actions=actions, level=self.level + 1)
        self.sub_panels.append(sub_panel)
        
        # 确保子面板被正确跟踪（与1.94.py一致）
        if sub_panel not in ActionPanel._open_panels:
            ActionPanel._open_panels.append(sub_panel)
            print(f"[DEBUG] 子面板已添加到跟踪列表: {sub_panel._panel_id}")
        
        # 显示子面板，隐藏当前面板
        sub_panel.move(self.pos())
        sub_panel.show()
        self.hide()
        
    def go_back(self):
        """返回上级面板"""
        self.hide()
        
        if self.parent_panel:
            self.parent_panel.show()
        else:
            # 寻找主悬浮按钮
            from PySide6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if (hasattr(widget, 'action_panel') and 
                    hasattr(widget, '__class__') and
                    widget.__class__.__name__ == 'FloatingButton'):
                    panel = getattr(widget, 'action_panel', None)
                    if panel:
                        panel.show()
                        break
                    
    def show_config_menu(self):
        """显示配置菜单"""
        menu = QMenu(self)
        menu.addAction("立即保存", lambda: self.save_config(force=True))
        menu.addAction("刷新界面", self.load_actions)
        menu.addAction("载入配置", self.load_config_from_backup)
        menu.addSeparator()
        
        # 粘贴功能
        paste_action = menu.addAction("粘贴", self.paste_action)
        # 检查是否有内容可粘贴
        if not ActionPanel._clipboard_action:
            paste_action.setEnabled(False)
        else:
            clip_name = ActionPanel._clipboard_action.get('name', '未知动作')
            clip_op = '剪切' if ActionPanel._clipboard_operation == 'cut' else '复制'
            paste_action.setText(f"粘贴 ({clip_op}: {clip_name})")
            
        menu.addSeparator()
        menu.addAction("备份信息", self.show_backup_info)
        menu.addAction("清理备份", self.cleanup_backups)
        menu.exec(QCursor.pos())
        
    def save_config(self, force: bool = False):
        """保存配置（默认只标记变化，退出时才保存文件）"""
        # 更新配置树
        root_config = self.get_root_config()
        config_manager.update_config(root_config)
        # 只有在强制保存时才立即保存到文件
        if force:
            config_manager.save_config(force=True)
        
    def show_backup_info(self):
        """显示备份信息（无声版本）"""
        info = config_manager.get_backup_info()
        
        message = (
            f"备份文件夹: {info['backup_dir']}\n"
            f"备份文件数量: {info['total_files']} 个\n"
            f"总大小: {info['total_size_mb']} MB\n"
            f"大小限制: {info['max_size_mb']} MB\n\n"
        )
        
        if info['files']:
            message += "最近的备份文件:\n"
            # 只显示最近的5个文件
            recent_files = info['files'][-5:]
            for file_info in reversed(recent_files):  # 最新的在前
                message += f"- {file_info['name']} ({file_info['size_kb']} KB, {file_info['modified']})\n"
        else:
            message += "暂无备份文件"
        
        # 使用自定义无声对话框
        dialog = SilentInfoDialog("备份信息", message, self)
        dialog.exec()
        
    def load_config_from_backup(self):
        """从备份文件中载入配置"""
        backup_info = config_manager.get_backup_info()
        
        if not backup_info['files']:
            QMessageBox.information(self, "提示", "没有可用的备份文件")
            return
            
        # 创建备份文件选择对话框
        dialog = BackupSelectionDialog(backup_info['files'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_backup = dialog.get_selected_backup()
            if selected_backup:
                self._load_backup_file(selected_backup)
                
    def _load_backup_file(self, backup_filename: str):
        """加载指定的备份文件"""
        try:
            backup_path = config_manager.backup_dir / backup_filename
            
            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认载入配置",
                f"确定要载入配置文件 '{backup_filename}' 吗？\n\n"
                "当前配置将被替换，建议先保存当前配置。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 先备份当前配置
                config_manager.save_config(force=True)
                
                # 加载备份配置
                success = config_manager.load_backup_config(backup_path)
                
                if success:
                    # 重新加载整个应用的配置
                    self._reload_entire_application()
                    QMessageBox.information(self, "成功", f"配置已从 '{backup_filename}' 载入")
                else:
                    QMessageBox.warning(self, "错误", "载入配置失败，请检查备份文件是否有效")
                    
        except Exception as e:
            QMessageBox.warning(self, "错误", f"载入配置时发生错误：{e}")
            
    def _reload_entire_application(self):
        """重新加载整个应用配置"""
        try:
            # 找到根面板
            root_panel = self
            while root_panel.parent_panel:
                root_panel = root_panel.parent_panel
                
            # 重新加载配置到根面板
            root_actions = config_manager.get("actions", [])
            root_panel.action_configs = root_actions
            root_panel.load_actions()
            
            # 关闭所有子面板
            for panel in ActionPanel._open_panels[:]:
                if panel != root_panel:
                    panel.hide()
                    
            # 只保留根面板在打开列表中
            ActionPanel._open_panels = [root_panel] if root_panel in ActionPanel._open_panels else []
            
            print("[载入配置] 应用配置已重新加载")
            
        except Exception as e:
            print(f"[载入配置] 重新加载应用配置失败: {e}")
        
    def cleanup_backups(self):
        """清理备份文件"""
        reply = QMessageBox.question(
            self, 
            "确认清理", 
            "是否清理超出大小限制的旧备份文件？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            cleaned_count = config_manager.manual_cleanup_backups()
            QMessageBox.information(
                self, 
                "清理完成", 
                f"已清理 {cleaned_count} 个老旧备份文件"
            )
        
    def get_root_config(self) -> Dict[str, Any]:
        """获取根配置"""
        # 找到根面板
        root_panel = self
        while root_panel.parent_panel:
            root_panel = root_panel.parent_panel
            
        # 构建配置
        config = config_manager.get_config()
        config["actions"] = self.build_action_tree(root_panel)
        return config
        
    def build_action_tree(self, panel: 'ActionPanel') -> List[Dict[str, Any]]:
        """构建动作树"""
        actions = []
        for i, action in enumerate(panel.action_configs):
            action_copy = action.copy()
            if action.get("type") == "panel":
                # 如果有对应的子面板实例，使用其动作
                if i < len(panel.sub_panels):
                    action_copy["actions"] = self.build_action_tree(panel.sub_panels[i])
                elif "actions" not in action_copy:
                    action_copy["actions"] = []
            actions.append(action_copy)
        return actions
        
    def execute_action_by_id(self, action_id: str):
        """通过动作ID执行动作"""
        # 查找动作
        action = None
        for act in self.action_configs:
            if act.get('id') == action_id:
                action = act
                break
                
        if not action:
            print(f"❌ 未找到动作 ID: {action_id}")
            return
            
        # 执行动作
        action_type = action.get('type')
        print(f"[DEBUG] 执行动作 [{action.get('name', '未命名')}] 类型: {action_type}")
        
        try:
            if action_type == "key":
                command = action.get("command", "")
                self.simulate_key(command)
            elif action_type == "program":
                command = action.get("command", "")
                self.run_program(command)
            elif action_type == "url":
                url = action.get("url", "")
                self.open_url(url)
            elif action_type == "text":
                text = action.get("text", "")
                self.send_text(text)
            elif action_type == "input_output":
                script_file = action.get("script_file", "")
                input_source = action.get("input_source", "clipboard")
                output_target = action.get("output_target", "text")
                self.execute_input_output(script_file, input_source, output_target)
            elif action_type == "quick_send":
                filename = action.get("filename", "")
                self.open_quick_send_panel(filename)
            elif action_type == "panel":
                actions = action.get("actions", [])
                self.open_sub_panel(actions)
            else:
                print(f"❌ 不支持的动作类型: {action_type}")
                
        except Exception as e:
            print(f"❌ 执行动作失败 [{action.get('name', '未命名')}]: {e}")
            
    def refresh_action_hotkeys(self):
        """刷新动作快捷键注册（从外部调用）"""
        # 这个方法由main.py中的QuickerApp调用
        pass
        
    # 动作执行方法
    def simulate_key(self, command: str):
        """模拟按键"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_simulate_key(command))
        
    def _switch_and_simulate_key(self, command: str):
        """切换窗口并模拟按键"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_simulate_key(command))
        else:
            self._execute_simulate_key(command)
            
    def open_quick_send_panel(self, filename: str = ""):
        """打开快捷发送面板
        
        Args:
            filename: 指定要打开的JSON文件名（不包含.json后缀）
        """
        try:
            from .quick_send_panel import QuickSendPanel
            
            # 检查是否已有快捷发送面板实例
            if hasattr(self, '_quick_send_panel') and self._quick_send_panel is not None:
                # 如果面板存在且可见，则隐藏
                if self._quick_send_panel.isVisible():
                    self._quick_send_panel.hide()
                    print("[DEBUG] 隐藏快捷发送面板")
                else:
                    # 如果面板存在但不可见，则显示
                    self._quick_send_panel.show()
                    self._quick_send_panel.raise_()
                    self._quick_send_panel.activateWindow()
                    print("[DEBUG] 显示快捷发送面板")
            else:
                # 创建新的面板实例
                self._quick_send_panel = QuickSendPanel(self, target_filename=filename)
                self._quick_send_panel.resize(500, 600)  # 设置默认窗口大小
                
                # 连接关闭信号，当面板关闭时清空引用
                def on_panel_finished():
                    self._quick_send_panel = None
                    print("[DEBUG] 快捷发送面板已关闭")
                
                self._quick_send_panel.finished.connect(on_panel_finished)
                
                # 使用show()而不是exec()来避免模态对话框
                self._quick_send_panel.show()
                print("[DEBUG] 创建并显示快捷发送面板")
                
        except Exception as e:
            print(f"打开快捷发送面板失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"打开快捷发送面板失败: {e}")
            
    def _execute_simulate_key(self, command: str):
        """执行按键模拟"""
        try:
            import pyautogui
            
            # 解析输入序列，支持以下格式：
            # 1. 组合键: ctrl+c, alt+tab
            # 2. 单个按键: f5, enter, space
            # 3. 文本串: "hello world"
            # 4. 延时等待: wait(1000) 表示等待1秒
            # 5. 序列组合: ctrl+c, wait(500), "pasted text", enter
            
            # 分割序列，支持逗号分隔
            sequence = [item.strip() for item in command.split(',')]
            
            for item in sequence:
                item = item.strip()
                if not item:
                    continue
                
                # 处理延时等待
                if item.startswith('wait(') and item.endswith(')'):
                    try:
                        delay_ms = int(item[5:-1])  # 提取括号内的数字
                        pyautogui.sleep(delay_ms / 1000.0)
                        continue
                    except ValueError:
                        print(f"延时格式错误: {item}，应为 wait(毫秒数)")
                        continue
                
                # 处理文本串（用引号包围的内容）
                if ((item.startswith('"') and item.endswith('"')) or 
                    (item.startswith("'") and item.endswith("'"))):
                    text = item[1:-1]  # 去掉引号
                    pyautogui.write(text)
                    continue
                
                # 处理组合键（包含+号）
                if '+' in item:
                    keys = [k.strip() for k in item.split('+')]
                    pyautogui.hotkey(*keys)
                else:
                    # 单个按键
                    pyautogui.press(item)
        except ImportError:
            QMessageBox.critical(self, "依赖缺失", 
                               "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"模拟按键失败：{e}")
        
    def run_program(self, command: str):
        """运行程序"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_run_program(command))
        
    def _switch_and_run_program(self, command: str):
        """切换窗口并运行程序"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_run_program(command))
        else:
            self._execute_run_program(command)
            
    def _execute_run_program(self, command: str):
        """执行运行程序"""
        try:
            import subprocess
            subprocess.Popen(command, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动程序：{e}")
        
    def open_url(self, url: str):
        """打开网址"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_open_url(url))
        
    def _switch_and_open_url(self, url: str):
        """切换窗口并打开网址"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_open_url(url))
        else:
            self._execute_open_url(url)
            
    def _execute_open_url(self, url: str):
        """执行打开网址"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开网址：{e}")
        
    def send_text(self, text: str):
        """发送文本"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_send_text(text))
        
    def _switch_and_send_text(self, text: str):
        """切换窗口并发送文本"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_send_text(text))
        else:
            self._execute_send_text(text)
            
    def _execute_send_text(self, text: str):
        """执行发送文本"""
        try:
            import pyautogui
            pyautogui.write(text)
        except ImportError:
            QMessageBox.critical(self, "依赖缺失", 
                               "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"发送文本失败：{e}")
            
    def execute_input_output(self, script_file: str, input_source: str, output_target: str):
        """执行输入输出动作"""
        # 隐藏面板并切换到上一个窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_execute_input_output(script_file, input_source, output_target))
        
    def _switch_and_execute_input_output(self, script_file: str, input_source: str, output_target: str):
        """切换窗口并执行输入输出动作"""
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._execute_input_output_action(script_file, input_source, output_target))
        else:
            self._execute_input_output_action(script_file, input_source, output_target)
            
    def _execute_input_output_action(self, script_file: str, input_source: str, output_target: str):
        """执行输入输出动作的具体实现"""
        try:
            # 获取输入文本
            input_text = self._get_input_text(input_source)
            
            # 执行脚本
            result = self._execute_script(script_file, input_text, input_source, output_target)
            
            # 处理输出
            if result is not None:
                self._handle_output(result, output_target)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"执行输入输出动作失败：{e}")
            
    def _get_input_text(self, input_source: str) -> str:
        """根据输入源获取输入文本"""
        try:
            if input_source == "clipboard":
                # 从剪贴板获取文本
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                return clipboard.text()
                
            elif input_source == "selection":
                # 从选中文本获取（模拟Ctrl+C然后获取剪贴板）
                import pyautogui
                pyautogui.hotkey('ctrl', 'c')
                QTimer.singleShot(100, lambda: None)  # 等待剪贴操作完成
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                return clipboard.text()
                
            elif input_source == "manual":
                # 手动输入
                text, ok = QInputDialog.getText(self, "输入文本", "请输入文本内容：")
                return text if ok else ""
                
            elif input_source == "none":
                # 无输入
                return ""
            else:
                return ""
                
        except ImportError as e:
            if "pyautogui" in str(e) and input_source == "selection":
                QMessageBox.warning(self, "依赖缺失", 
                                   "需要安装 'pyautogui' 库来支持选中文本功能。\n请运行: pip install pyautogui")
            return ""
        except Exception as e:
            print(f"获取输入文本失败: {e}")
            return ""
            
    def _execute_script(self, script_file: str, input_text: str, input_source: str, output_target: str) -> str:
        """执行脚本文件"""
        try:
            script_path = config_manager.get_input_output_script_path(script_file)
            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_path}")
                
            # 读取脚本内容
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
                
            # 执行脚本
            namespace = {
                'input_text': input_text,
                'input_source': input_source,
                'output_target': output_target
            }
            
            exec(script_content, namespace)
            
            # 调用process函数
            if 'process' in namespace and callable(namespace['process']):
                result = namespace['process'](input_text, input_source, output_target)
                return str(result) if result is not None else ""
            else:
                raise ValueError("脚本中未找到process函数")
                
        except Exception as e:
            print(f"执行脚本失败: {e}")
            raise
            
    def _handle_output(self, result: str, output_target: str):
        """处理输出结果"""
        try:
            if output_target == "text":
                # 发送文本
                import pyautogui
                pyautogui.write(result)
                
            elif output_target == "url":
                # 打开网址
                import webbrowser
                webbrowser.open(result)
                
            elif output_target == "clipboard":
                # 复制到剪贴板
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                clipboard.setText(result)
                
            elif output_target == "file":
                # 保存到文件
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"output_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"结果已保存到: {filename}")
                
            elif output_target == "window":
                # 显示窗口
                dialog = SilentInfoDialog("输入输出结果", result, self)
                dialog.exec()
                
        except ImportError as e:
            if "pyautogui" in str(e) and output_target == "text":
                QMessageBox.warning(self, "依赖缺失", 
                                   "需要安装 'pyautogui' 库来支持文本输出功能。\n请运行: pip install pyautogui")
        except Exception as e:
            print(f"处理输出失败: {e}")
            
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
            parent = parent.parent()
        return None