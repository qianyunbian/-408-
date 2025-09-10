import sys
import json
import subprocess
import glob
import os
try:
    import pyautogui
except ImportError:
    pyautogui = None

# 导入 win32gui 和 win32con
if sys.platform == "win32":
    try:
        import win32gui
        import win32con
    except ImportError:
        win32gui = None
        win32con = None
else:
    win32gui = None
    win32con = None

from PySide6.QtGui import QAction, QGuiApplication, QIcon, QCursor, QDrag, QPixmap, QClipboard
from PySide6.QtCore import Qt, QPoint, QTimer, QRect, QMimeData, QEventLoop
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QMenu,
    QSystemTrayIcon, QMessageBox, QGridLayout, QLabel, QVBoxLayout,
    QInputDialog
)

CONFIG = {}

def load_config(config_dir="."):
    """加载最新的配置文件"""
    global CONFIG

    # 查找当前目录下所有 config_ 开头的文件
    config_files = glob.glob(os.path.join(config_dir, "config_*"))
    if not config_files:
        msg = "未找到任何配置文件！"
        print(f"错误：{msg}")
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "配置错误", msg)
        sys.exit(1)

    # 按文件修改时间排序，取最新的
    latest_file = max(config_files, key=os.path.getmtime)

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)
        print(f"已加载配置文件: {latest_file}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        msg = f"无法加载或解析配置文件 '{latest_file}': {e}"
        print(f"错误：{msg}")
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "配置错误", msg)
        sys.exit(1)


class DraggableButton(QPushButton):
    """可拖动的按钮"""
    def __init__(self, text, parent):
        super().__init__(text, parent)
        btn_config = CONFIG.get("action_buttons", {})
        style_config = btn_config.get("style", {})
        
        self.setFixedSize(btn_config.get("size", 60), btn_config.get("size", 60))
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {style_config.get("background_color", "#fff")};
                border: {style_config.get("border", "1px solid #ddd")};
                border-radius: {style_config.get("border_radius", 8)}px;
                font-size: {style_config.get("font_size", 12)}px;
                color: {style_config.get("color", "#333")};
            }}
            QPushButton:hover {{
                background-color: {style_config.get("hover_background_color", "#f0f8ff")};
                border-color: {style_config.get("hover_border_color", "#4f7cff")};
            }}
            QPushButton:pressed {{
                background-color: {style_config.get("pressed_background_color", "#e0f0ff")};
            }}
        """)
        self._is_dragging = False
        print(f"DraggableButton initialized with text: {text}")

    def mousePressEvent(self, e):
        print(f"DraggableButton.mousePressEvent called with button: {e.button()}")
        if e.button() == Qt.LeftButton:
            print("Left button pressed on DraggableButton")
            self.start_pos = e.position().toPoint()
            self._is_dragging = False
        super().mousePressEvent(e)
        print("DraggableButton.mousePressEvent finished")

    def mouseMoveEvent(self, e):
        print(f"mouseMoveEvent called with buttons: {e.buttons()}")
        if not (e.buttons() & Qt.LeftButton):
            print("Not left button, returning")
            return
        if (e.position().toPoint() - self.start_pos).manhattanLength() < QApplication.startDragDistance():
            print("Not enough distance for drag, returning")
            return

        print("Starting drag operation")
        self._is_dragging = True
        
        panel = self.parent()
        if not panel: 
            print("No parent panel, returning")
            return
        panel._dragged_button = self

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData('application/x-dnd-button', b'')
        drag.setMimeData(mime_data)

        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(e.position().toPoint())

        self.hide()
        drag.exec(Qt.MoveAction)
        
        if panel:
            panel._dragged_button = None
        
        if self.isHidden():
            self.show()

    def mouseReleaseEvent(self, e):
        print(f"DraggableButton.mouseReleaseEvent called with button: {e.button()}")
        if e.button() == Qt.LeftButton:
            print("Left button released on DraggableButton")
            if not self._is_dragging:
                print("Not dragging on DraggableButton, emitting clicked signal")
                self.clicked.emit()
            self._is_dragging = False
        super().mouseReleaseEvent(e)
        print("DraggableButton.mouseReleaseEvent finished")


class ActionPanel(QWidget):
    """快捷功能面板"""
    def __init__(self, parent=None, actions=None, level=0):
        super().__init__(parent)
        self._dragged_button = None
        self._current_placeholder_index = -1
        self.level = level
        self.actions = actions if actions is not None else CONFIG.get("actions", [])
        self.parent_panel = parent if isinstance(parent, ActionPanel) else None
        self.previous_active_window = None # 用于存储"最后的非自己窗口"句柄
        self._current_right_click_button = None  # 用于跟踪当前右键点击的按钮

        panel_config = CONFIG.get("action_panel", {})
        btn_config = CONFIG.get("action_buttons", {})

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.Popup
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {panel_config.get("background_color", "rgba(240, 240, 240, 0.95)")};
                border-radius: 10px;
                border: 1px solid #ccc;
            }}
        """)
        self.setFixedSize(panel_config.get("width", 300), panel_config.get("height", 375))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("Quicker")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; border: none; background: transparent;")
        main_layout.addWidget(title_label)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(btn_config.get("spacing", 10))
        main_layout.addLayout(self.grid_layout)
        
        if self.level > 0:
            back_button = QPushButton("返回")
            back_button.clicked.connect(self.go_back)
            main_layout.addWidget(back_button)

        main_layout.addStretch()

        self.setAcceptDrops(True)
        
        self.buttons = []
        self.drop_placeholder = QWidget()
        btn_size = btn_config.get("size", 60)
        self.drop_placeholder.setFixedSize(btn_size, btn_size)
        self.drop_placeholder.setStyleSheet("background-color: transparent; border: 2px dashed #999; border-radius: 8px;")

        self.load_actions()

    def go_back(self):
        self.close()
        if self.parent_panel:
            self.parent_panel.show()

    def load_actions(self):
        for button in self.buttons:
            button.deleteLater()
        self.buttons.clear()

        for action_config in self.actions:
            name = action_config.get("name", "Unnamed")
            action_type = action_config.get("type")
            command = action_config.get("command")
            args = action_config.get("args", [])
            sub_actions = action_config.get("actions")

            callback = None
            if action_type == "program":
                callback = lambda _, cmd=command: self.run_program(cmd)
            elif action_type == "command":
                callback = lambda _, cmd=command, a=args: self.run_command(cmd, a)
            elif action_type == "placeholder":
                callback = lambda _, n=name: self.show_placeholder(n)
            elif action_type == "panel":
                callback = lambda _, sub_acts=sub_actions: self.open_sub_panel(sub_acts)
            elif action_type == "send_clipboard_with_parentheses":
                callback = self.send_clipboard_with_parentheses
            elif action_type == "key":
                callback = lambda _, cmd=command: self.simulate_key(cmd)
            elif action_type == "url":
                callback = lambda _, url=command: self.open_url(url)
            elif action_type == "text":
                callback = lambda _, txt=command: self.send_text(txt)
            
            if callback:
                button = self.create_action_button(name, callback)
                self.buttons.append(button)
        
        self._relayout_buttons()

    def _relayout_buttons(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        columns = CONFIG.get("action_panel", {}).get("columns", 4)
        for i, widget in enumerate(self.buttons):
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(widget, row, col)

        # 添加占位符以填充网格
        num_buttons = len(self.buttons)
        if columns > 0 and num_buttons % columns != 0:
            placeholders_to_add = columns - (num_buttons % columns)
            start_index = num_buttons
            btn_config = CONFIG.get("action_buttons", {})
            btn_size = btn_config.get("size", 60)

            for i in range(placeholders_to_add):
                placeholder = QWidget()
                placeholder.setFixedSize(btn_size, btn_size)
                placeholder.setStyleSheet("background-color: transparent; border: 1px dashed #ccc; border-radius: 8px;")
                
                current_index = start_index + i
                row = current_index // columns
                col = current_index % columns
                self.grid_layout.addWidget(placeholder, row, col)

        # 在最后增加一个"新增动作"按钮
        add_btn = QPushButton("+")
        btn_config = CONFIG.get("action_buttons", {})
        btn_size = btn_config.get("size", 60)
        add_btn.setFixedSize(btn_size, btn_size)
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                color: #4f7cff;
                border: 2px dashed #4f7cff;
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
        row = (len(self.buttons)) // columns
        col = (len(self.buttons)) % columns
        self.grid_layout.addWidget(add_btn, row, col)

        # 添加配置管理按钮
        config_btn = QPushButton("⚙")
        config_btn.setFixedSize(btn_size, btn_size)
        config_btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                color: #666;
                border: 2px dashed #ccc;
                background: #f8f8f8;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #e8e8e8;
                color: #333;
                border-color: #999;
            }
        """)
        config_btn.setToolTip("配置管理")
        config_btn.clicked.connect(self.show_config_menu)
        row = (len(self.buttons) + 1) // columns
        col = (len(self.buttons) + 1) % columns
        self.grid_layout.addWidget(config_btn, row, col)

    def add_new_action(self):
        menu = QMenu(self)
        menu.addAction("模拟按键", lambda: self.create_new_action("key"))
        menu.addAction("运行程序或文件", lambda: self.create_new_action("program"))
        menu.addAction("打开网址", lambda: self.create_new_action("url"))
        menu.addAction("发送文本", lambda: self.create_new_action("text"))
        menu.exec(QCursor.pos())

    def create_new_action(self, action_type):
        # 根据类型弹出输入框
        if action_type == "key":
            text, ok = QInputDialog.getText(self, "新增动作", 
                "请输入要模拟的按键序列：\n\n"
                "支持格式：\n"
                "• 组合键: ctrl+c, alt+tab\n"
                "• 单个按键: f5, enter, space\n"
                "• 文本串: \"hello world\"\n"
                "• 延时等待: wait(1000)\n"
                "• 序列组合: ctrl+c, wait(500), \"text\", enter")
            if not ok or not text.strip():
                return
            new_action = {"name": f"模拟按键", "type": "key", "command": text.strip()}
        elif action_type == "program":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入程序路径或文件路径：")
            if not ok or not text.strip():
                return
            new_action = {"name": f"运行程序", "type": "program", "command": text.strip()}
        elif action_type == "url":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入网址（URL）：")
            if not ok or not text.strip():
                return
            new_action = {"name": f"打开网址", "type": "url", "command": text.strip()}
        elif action_type == "text":
            text, ok = QInputDialog.getText(self, "新增动作", "请输入要发送的文本内容：")
            if not ok or not text.strip():
                return
            new_action = {"name": f"发送文本", "type": "text", "command": text.strip()}
        else:
            return
        # 新增动作后立即生成新的配置文件（带时间戳），而不是覆盖旧的
        # 这样每次添加都会保留历史版本
        # self.save_config_to_file()  # 移除重复调用

        self.actions.append(new_action)
        # 保存到配置文件
        CONFIG["actions"] = self.actions
        if self.save_config_to_file():
            self.load_actions()
        else:
            # 如果保存失败，移除刚添加的动作
            self.actions.pop()

    def open_sub_panel(self, actions):
        if self.level >= 4:  # Max 5 levels (0 to 4)
            QMessageBox.warning(self, "提示", "已达到最大层级。")
            return

        sub_panel = ActionPanel(parent=self, actions=actions, level=self.level + 1)
        sub_panel.move(self.pos())
        sub_panel.show()
        self.hide()

    def create_action_button(self, name, callback):
        button = DraggableButton(name, self)
        button.clicked.connect(callback)
        return button

    def get_grid_index(self, pos: QPoint):
        layout_rect = self.grid_layout.geometry()
        if not layout_rect.contains(pos):
            pos.setX(max(layout_rect.left(), min(pos.x(), layout_rect.right())))
            pos.setY(max(layout_rect.top(), min(pos.y(), layout_rect.bottom())))

        relative_pos = pos - layout_rect.topLeft()
        
        btn_config = CONFIG.get("action_buttons", {})
        cell_width = btn_config.get("size", 60) + self.grid_layout.spacing()
        cell_height = btn_config.get("size", 60) + self.grid_layout.spacing()

        if cell_width <= 0 or cell_height <= 0: return 0

        row = relative_pos.y() // cell_height
        col = relative_pos.x() // cell_width
        
        columns = CONFIG.get("action_panel", {}).get("columns", 4)
        row = max(0, row)
        col = max(0, min(col, columns - 1))
        
        index = row * columns + col
        return min(index, len(self.buttons))

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('application/x-dnd-button') and self._dragged_button:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if not e.mimeData().hasFormat('application/x-dnd-button'):
            e.ignore()
            return

        target_index = self.get_grid_index(e.position().toPoint())
        
        if target_index == self._current_placeholder_index:
            e.accept()
            return
            
        self._current_placeholder_index = target_index

        # 临时按钮列表，用于布局
        temp_buttons = self.buttons[:]
        if self._dragged_button in temp_buttons:
            temp_buttons.remove(self._dragged_button)
        
        # 确保目标索引有效
        target_index = min(target_index, len(temp_buttons))
        
        # 插入占位符
        temp_buttons.insert(target_index, self.drop_placeholder)

        # 重新布局
        columns = CONFIG.get("action_panel", {}).get("columns", 4)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        for i, widget in enumerate(temp_buttons):
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(widget, row, col)
            if widget == self.drop_placeholder:
                widget.show()

        e.accept()

    def dropEvent(self, e):
        if not self._dragged_button:
            e.ignore()
            return

        # 移除占位符
        if self.drop_placeholder.parent():
            self.grid_layout.removeWidget(self.drop_placeholder)
            self.drop_placeholder.setParent(None)

        # 获取源索引和目标索引
        try:
            source_index = self.buttons.index(self._dragged_button)
        except ValueError:
            source_index = -1

        target_index = self.get_grid_index(e.position().toPoint())

        if source_index != -1 and source_index != target_index:
            # 如果目标索引有效且在范围内，则交换
            if target_index < len(self.buttons):
                # 交换
                self.buttons[source_index], self.buttons[target_index] = \
                    self.buttons[target_index], self.buttons[source_index]
            else:
                # 如果目标超出范围（拖到末尾），则移动到末尾
                btn = self.buttons.pop(source_index)
                self.buttons.append(btn)

        self._relayout_buttons()

        if self._dragged_button:
            self._dragged_button.show()
        self._dragged_button = None
        self._current_placeholder_index = -1
        e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        # 拖动离开窗口时，恢复原始状态
        if self.drop_placeholder.parent():
            self.grid_layout.removeWidget(self.drop_placeholder)
            self.drop_placeholder.setParent(None)
        
        if self._dragged_button:
            if self._dragged_button not in self.buttons:
                self.buttons.append(self._dragged_button)
            self._relayout_buttons()
            self._dragged_button.show()
        
        e.accept()

    def _set_clipboard_text_with_retry(self, text, mode=QClipboard.Mode.Clipboard, retries=5, delay=50):
        """
        尝试多次设置剪贴板文本，以处理访问冲突。
        返回 True 表示成功，False 表示失败。
        """
        clipboard = QGuiApplication.clipboard()
        for i in range(retries):
            try:
                clipboard.setText(text, mode)
                if clipboard.text(mode) == text:
                    return True
            except Exception:
                pass
            loop = QEventLoop()
            QTimer.singleShot(delay, loop.quit)
            loop.exec()
        
        QMessageBox.warning(self, "剪贴板错误", "无法访问剪贴板，请稍后重试。")
        return False

    def send_clipboard_with_parentheses(self):
        """获取剪贴板文本，添加括号并发送。"""
        if win32gui:
            parent = self.parent()
            self.previous_active_window = getattr(parent, "last_foreground_window", None)
        if not pyautogui:
            QMessageBox.critical(self, "依赖缺失", "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
            return

        clipboard = QGuiApplication.clipboard()
        original_text = clipboard.text()

        if not original_text:
            QMessageBox.information(self, "提示", "剪贴板中没有文本。")
            return

        text_to_send = f"({original_text})"
        if not self._set_clipboard_text_with_retry(text_to_send):
            return

        self.hide()
        QTimer.singleShot(300, lambda: self._do_paste_and_restore(original_text_to_restore=original_text))

    def _do_paste_and_restore(self, original_text_to_restore):
        """切换焦点并准备粘贴"""
        if win32gui and self.previous_active_window:
            try:
                placement = win32gui.GetWindowPlacement(self.previous_active_window)
                if placement[1] == win32con.SW_SHOWMINIMIZED:
                    win32gui.ShowWindow(self.previous_active_window, win32con.SW_RESTORE)
                elif placement[1] == win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(self.previous_active_window, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(self.previous_active_window)
                QTimer.singleShot(200, lambda: self._perform_paste_and_restore_clipboard(original_text_to_restore))
                return
            except Exception:
                pass

        self._perform_paste_and_restore_clipboard(original_text_to_restore)

    def _perform_paste_and_restore_clipboard(self, original_text):
        """执行粘贴并恢复剪贴板"""
        try:
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pass
        finally:
            QTimer.singleShot(150, lambda: self._set_clipboard_text_with_retry(original_text))

    def _switch_to_previous_window(self):
        """切换到上一个活动窗口"""
        if win32gui and self.previous_active_window:
            try:
                placement = win32gui.GetWindowPlacement(self.previous_active_window)
                if placement[1] == win32con.SW_SHOWMINIMIZED:
                    win32gui.ShowWindow(self.previous_active_window, win32con.SW_RESTORE)
                elif placement[1] == win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(self.previous_active_window, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(self.previous_active_window)
                return True
            except Exception:
                pass
        return False

    def simulate_key(self, key_str):
        """模拟按键动作，支持输入序列、组合键、单个按键、文本串和延时等待"""
        if not pyautogui:
            QMessageBox.critical(self, "依赖缺失", "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
            return
        
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._simulate_key_action(key_str))

    def _simulate_key_action(self, key_str):
        """执行按键模拟操作"""
        try:
            # 解析输入序列，支持以下格式：
            # 1. 组合键: ctrl+c, alt+tab
            # 2. 单个按键: f5, enter, space
            # 3. 文本串: "hello world"
            # 4. 延时等待: wait(1000) 表示等待1秒
            # 5. 序列组合: ctrl+c, wait(500), "pasted text", enter
            
            # 分割序列，支持逗号分隔
            sequence = [item.strip() for item in key_str.split(',')]
            
            for item in sequence:
                item = item.strip()
                if not item:
                    continue
                
                # 处理延时等待
                if item.startswith('wait(') and item.endswith(')'):
                    try:
                        delay_ms = int(item[5:-1])  # 提取括号内的数字
                        # 使用QTimer实现非阻塞延时
                        loop = QEventLoop()
                        QTimer.singleShot(delay_ms, loop.quit)
                        loop.exec()
                        continue
                    except ValueError:
                        QMessageBox.warning(self, "延时格式错误", f"延时格式错误: {item}，应为 wait(毫秒数)")
                        continue
                
                # 处理文本串（用引号包围的内容）
                if (item.startswith('"') and item.endswith('"')) or \
                   (item.startswith("'") and item.endswith("'")):
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
            
            self.hide()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"模拟按键失败：{e}")

    def open_url(self, url):
        import webbrowser
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._open_url_action(url))

    def _open_url_action(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
            self.hide()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开网址：{e}")

    def send_text(self, text):
        if not pyautogui:
            QMessageBox.critical(self, "依赖缺失", "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
            return
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._send_text_action(text))

    def _send_text_action(self, text):
        try:
            pyautogui.write(text)
            self.hide()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"发送文本失败：{e}")

    def run_program(self, program_path):
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._run_program_action(program_path))

    def _run_program_action(self, program_path):
        try:
            subprocess.Popen(program_path)
            self.hide()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动程序：{e}")

    def run_command(self, command, args=None):
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._run_command_action(command, args))

    def _run_command_action(self, command, args=None):
        try:
            cmd_list = [command] + (args or [])
            subprocess.Popen(cmd_list)
            self.hide()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法执行命令：{e}")

    def show_placeholder(self, feature_name):
        # 切换到上一个活动窗口
        self._switch_to_previous_window()
        QTimer.singleShot(200, lambda: self._show_placeholder_action(feature_name))

    def _show_placeholder_action(self, feature_name):
        QMessageBox.information(self, "提示", f"'{feature_name}' 功能尚未实现。")
        self.hide()

    def save_config_to_file(self, file_path="config"):
        """简化的配置文件保存功能，每次保存都生成新的配置文件"""
        import os
        import time
        
        # 生成带时间戳的新文件名
        timestamp = int(time.time())
        base_name = os.path.splitext(file_path)[0]
        extension = os.path.splitext(file_path)[1] if os.path.splitext(file_path)[1] else ""
        new_file_path = f"{base_name}_{timestamp}{extension}"
        
        print(f"正在保存配置到新文件: {new_file_path}")
        
        try:
            # 直接写入新文件
            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(CONFIG, f, ensure_ascii=False, indent=2)
            
            # 验证保存是否成功
            if os.path.exists(new_file_path) and os.path.getsize(new_file_path) > 0:
                print(f"配置保存成功: {new_file_path}")
                # 保存成功后，更新全局配置文件路径
                self._update_config_file_reference(new_file_path)
                return True
            else:
                raise Exception("文件写入后验证失败")
                
        except Exception as e:
            print(f"配置保存失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存配置文件：{e}")
            return False

    def _update_config_file_reference(self, new_file_path):
        """更新配置文件引用，保持向后兼容"""
        import os
        import time
        
        # 简化版本：只记录日志，不创建链接以避免权限问题
        try:
            print(f"配置文件已保存到: {new_file_path}")
            print(f"可以使用此文件路径来加载配置")
            
            # 可选：创建一个简单的文本文件记录最新配置路径
            latest_info_file = "latest_config.txt"
            try:
                with open(latest_info_file, 'w', encoding='utf-8') as f:
                    f.write(f"最新配置文件: {new_file_path}\n")
                    f.write(f"保存时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                print(f"已更新最新配置信息文件: {latest_info_file}")
            except Exception as e:
                print(f"更新配置信息文件失败: {e}")
                
        except Exception as e:
            print(f"更新配置文件引用失败: {e}")

    def get_config_file_list(self):
        """获取所有配置文件列表"""
        import os
        import glob
        
        base_name = os.path.splitext("config")[0]
        extension = os.path.splitext("config")[1] if os.path.splitext("config")[1] else ""
        
        # 查找所有配置文件
        pattern = f"{base_name}_*{extension}"
        config_files = glob.glob(pattern)
        
        # 按时间戳排序（最新的在前）
        config_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return config_files

    def show_config_file_history(self):
        """显示配置文件历史"""
        config_files = self.get_config_file_list()
        
        if not config_files:
            QMessageBox.information(self, "配置文件历史", "没有找到历史配置文件")
            return
        
        # 创建历史文件选择对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout
        
        import os
        import time

        dialog = QDialog(self)
        dialog.setWindowTitle("配置文件历史")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 文件列表
        list_widget = QListWidget()
        for config_file in config_files:
            # 获取文件信息
            stat = os.stat(config_file)
            file_size = stat.st_size
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            
            item_text = f"{os.path.basename(config_file)} - {mod_time} ({file_size} bytes)"
            list_widget.addItem(item_text)
        
        layout.addWidget(list_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("加载选中配置")
        load_btn.clicked.connect(lambda: self._load_selected_config(list_widget, config_files, dialog))
        
        delete_btn = QPushButton("删除选中配置")
        delete_btn.clicked.connect(lambda: self._delete_selected_config(list_widget, config_files))
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(load_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec()

    def _load_selected_config(self, list_widget, config_files, dialog):
        """加载选中的配置文件"""
        current_row = list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个配置文件")
            return
        
        selected_file = config_files[current_row]
        
        try:
            # 加载选中的配置
            load_config(selected_file)
            self.load_actions()
            QMessageBox.information(self, "成功", f"已加载配置文件: {os.path.basename(selected_file)}")
            dialog.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置文件失败: {e}")

    def _delete_selected_config(self, list_widget, config_files):
        """删除选中的配置文件"""
        current_row = list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个配置文件")
            return
        
        selected_file = config_files[current_row]
        
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除配置文件 {os.path.basename(selected_file)} 吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import os
                os.remove(selected_file)
                list_widget.takeItem(current_row)
                config_files.pop(current_row)
                QMessageBox.information(self, "成功", "配置文件已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除配置文件失败: {e}")

    def show_config_menu(self):
        """显示配置管理菜单"""
        menu = QMenu(self)
        menu.addAction("查看配置文件历史", self.show_config_file_history)
        menu.addAction("备份当前配置", self.backup_config)
        menu.addAction("恢复配置", self.restore_config)
        menu.addAction("验证配置", self.validate_config)
        menu.addAction("重新加载配置", self.reload_config)
        menu.addAction("退出", self.close)
        menu.exec(QCursor.pos())

    def backup_config(self):
        """备份当前配置"""
        if self.save_config_to_file():
            QMessageBox.information(self, "备份成功", "配置已备份到新文件")
        else:
            QMessageBox.warning(self, "备份失败", "无法备份配置。")

    def restore_config(self):
        """恢复配置"""
        import os
        import shutil
        
        # 恢复到最新的历史配置
        config_files = self.get_config_file_list()
        if not config_files:
            QMessageBox.warning(self, "备份不存在", "未找到历史配置文件。")
            return
        
        latest_file = config_files[0]
        try:
            shutil.copy2(latest_file, "config")
            QMessageBox.information(self, "恢复成功", f"配置已从 '{os.path.basename(latest_file)}' 恢复到 'config'。")
            self.load_actions() # 重新加载配置以应用更改
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"无法恢复配置：{e}")

    def validate_config(self):
        """验证配置文件是否有效"""
        import json
        try:
            with open("config", "r", encoding="utf-8") as f:
                json.load(f)
            QMessageBox.information(self, "验证成功", "配置文件有效。")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.warning(self, "验证失败", f"配置文件无效：{e}")
        except Exception as e:
            QMessageBox.warning(self, "验证失败", f"验证过程中发生错误：{e}")

    def reload_config(self):
        """重新加载配置文件"""
        load_config()
        QMessageBox.information(self, "配置重载", "配置已重新加载。")
        self.load_actions()

    def mousePressEvent(self, event):
        """处理面板上的鼠标按下事件"""
        if event.button() == Qt.RightButton:
            print(f"ActionPanel right-clicked at position: {event.pos()}")
            # 检查是否在某个按钮上右键点击
            clicked_widget = self.childAt(event.pos())
            if isinstance(clicked_widget, DraggableButton):
                print(f"Right-clicked on button: {clicked_widget.text()}")
                self._current_right_click_button = clicked_widget
                self.show_context_menu(event.pos())
            else:
                print("Right-clicked on panel (not on a button)")
                self._current_right_click_button = None
                # 如果需要在面板空白处也显示菜单，可以在这里添加
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        """显示右键菜单"""
        print(f"show_context_menu called with position: {position}")
        menu = QMenu()
        
        # 如果右键点击的是按钮，则显示删除选项
        if self._current_right_click_button:
            delete_action = menu.addAction("删除")
            menu.addSeparator()
            
        cancel_action = menu.addAction("取消")
        print("Menu created with available actions")
        
        action = menu.exec(self.mapToGlobal(position))
        print(f"Menu executed, selected action: {action}")
        
        if self._current_right_click_button and action == delete_action:
            print("Delete action selected")
            self.delete_action(self._current_right_click_button)
        elif action == cancel_action:
            print("Cancel action selected")
            # 取消操作，不执行任何功能
            print("Cancel operation completed")
        else:
            print("No action selected or menu cancelled")
            
        # 重置当前右键点击的按钮
        self._current_right_click_button = None

    def delete_action(self, button):
        """删除指定按钮对应的动作"""
        print(f"delete_action called for button: {button.text()}")
        # 查找按钮在按钮列表中的索引
        try:
            index = self.buttons.index(button)
            print(f"Button index in panel: {index}")
            # 从面板的动作列表中删除对应的动作
            if 0 <= index < len(self.actions):
                self.actions.pop(index)
                print("Action removed from panel.actions")
                # 更新配置并保存
                CONFIG["actions"] = self.actions
                print("CONFIG updated")
                if self.save_config_to_file():
                    print("Config saved successfully")
                    # 重新加载动作按钮
                    self.load_actions()
                    print("Actions reloaded")
                else:
                    # 如果保存失败，恢复动作
                    print("Failed to save config")
                    self.actions.insert(index, CONFIG.get("actions", [])[index])
        except (ValueError, IndexError) as e:
            print(f"Exception in delete_action: {e}")
            pass


class FloatingButton(QWidget):
    def __init__(self):
        super().__init__()
        fb_config = CONFIG.get("floating_button", {})
        style_config = fb_config.get("style", {})
        size = fb_config.get("size", 68)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(size, size)

        self.button = QPushButton("Q", self)
        self.button.setGeometry(0, 0, size, size)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setStyleSheet(f"""
            QPushButton {{
                border-radius: {size // 2}px;
                background: {style_config.get("background", "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f7cff, stop:1 #6ce0ff)")};
                color: {style_config.get("color", "white")};
                font-size: {style_config.get("font_size", 20)}px;
                font-weight: {style_config.get("font_weight", 700)};
                border: 0px; 
            }}
            QPushButton:hover {{
                background: {style_config.get("hover_background", "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #608cff, stop:1 #7cf0ff)")};
            }}
            QPushButton:pressed {{ background: #3b5ed6; }}
        """)

        self.menu = QMenu()
        act_about = QAction("关于", self, triggered=self.show_about)
        act_autostart = QAction("开机自启（占位）", self, checkable=True)
        act_quit = QAction("退出", self, triggered=QApplication.instance().quit)
        self.menu.addActions([act_about, act_autostart, act_quit])
        self.button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.button.customContextMenuRequested.connect(
            lambda: self.menu.exec(self.mapToGlobal(QPoint(self.width() // 2, self.height())))
        )

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon.fromTheme("applications-system"))
        self.tray.setToolTip("Floating Quick Button")
        self.tray.setContextMenu(self.menu)
        self.tray.show()

        self.move_to_right_middle()

        self._drag_pos: QPoint | None = None
        self._mouse_press_pos: QPoint | None = None
        self._is_dragging = False
        self.snap_margin = fb_config.get("snap_margin", 10)
        self.edge_auto_snap = True

        self.idle_opacity = fb_config.get("idle_opacity", 0.6)
        self.active_opacity = fb_config.get("active_opacity", 1.0)
        self.setWindowOpacity(self.idle_opacity)
        self.button.installEventFilter(self)

        self.guard = QTimer(self)
        self.guard.timeout.connect(self.ensure_in_screen)
        self.guard.start(2500)

        self.button.mousePressEvent = self.button_mousePressEvent
        self.button.mouseMoveEvent = self.button_mouseMoveEvent
        self.button.mouseReleaseEvent = self.button_mouseReleaseEvent

        self.action_panel = None

        # 新增：持续记录“最后的非自己窗口”句柄
        self.last_foreground_window = None
        self.last_foreground_timer = QTimer(self)
        self.last_foreground_timer.timeout.connect(self.update_last_foreground_window)
        self.last_foreground_timer.start(500)  # 每 500ms 检查一次

    def update_last_foreground_window(self):
        if win32gui:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd != int(self.winId()) and hwnd != 0:
                    self.last_foreground_window = hwnd
            except Exception:
                pass

    def show_about(self):
        QMessageBox.information(self, "关于", "这是一个悬浮按钮程序示例，样式类似 Quicker。\n作者：Your Name\n版本：1.0")

    def on_click(self):
        visible_panels = [w for w in QApplication.topLevelWidgets() if isinstance(w, ActionPanel) and w.isVisible()]

        if self.action_panel is None:
            self.action_panel = ActionPanel(parent=self)

        is_main_panel_visible = self.action_panel.isVisible()

        for panel in visible_panels:
            panel.hide()

        if not is_main_panel_visible:
            self.action_panel.previous_active_window = self.last_foreground_window

            btn_geo = self.geometry()
            panel_size = self.action_panel.size()
            screen_geo = self.normalized_screen_geo()
            pos_x = btn_geo.right() + 10
            pos_y = btn_geo.center().y() - panel_size.height() // 2
            if pos_x + panel_size.width() > screen_geo.right():
                pos_x = btn_geo.left() - panel_size.width() - 10
            pos_y = max(screen_geo.top(), min(pos_y, screen_geo.bottom() - panel_size.height()))
            self.action_panel.move(pos_x, pos_y)
            self.action_panel.show()

    def button_mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._mouse_press_pos = e.globalPosition().toPoint()
            self._is_dragging = False

    def button_mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self._drag_pos is not None:
            if not self._is_dragging and (e.globalPosition().toPoint() - self._mouse_press_pos).manhattanLength() > QApplication.startDragDistance():
                self._is_dragging = True
            if self._is_dragging:
                self.move(e.globalPosition().toPoint() - self._drag_pos)

    def button_mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._is_dragging:
                if self.edge_auto_snap:
                    self.snap_to_edges()
            else:
                self.on_click()
            self._drag_pos = None
            self._mouse_press_pos = None
            self._is_dragging = False

    def snap_to_edges(self):
        geo = self.normalized_screen_geo()
        w, h = self.width(), self.height()
        x, y = self.x(), self.y()
        d_left, d_right = abs(x - geo.left()), abs(geo.right() - (x + w))
        d_top, d_bottom = abs(y - geo.top()), abs(geo.bottom() - (y + h))
        nearest = min(d_left, d_right, d_top, d_bottom)
        if nearest <= max(self.snap_margin, 30):
            if nearest == d_left: x = geo.left()
            elif nearest == d_right: x = geo.right() - w
            elif nearest == d_top: y = geo.top()
            elif nearest == d_bottom: y = geo.bottom() - h
            self.move(x, y)

    def move_to_right_middle(self):
        geo = self.normalized_screen_geo()
        x = geo.right() - self.width() - 12
        y = geo.top() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def normalized_screen_geo(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def ensure_in_screen(self):
        geo = self.normalized_screen_geo()
        x = min(max(self.x(), geo.left()), geo.right() - self.width())
        y = min(max(self.y(), geo.top()), geo.bottom() - self.height())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def eventFilter(self, obj, ev):
        if obj is self.button:
            if ev.type() == ev.Type.Enter:
                self.setWindowOpacity(self.active_opacity)
            elif ev.type() == ev.Type.Leave:
                self.setWindowOpacity(self.idle_opacity)
        return super().eventFilter(obj, ev)

    def mouseDoubleClickEvent(self, e):
        e.ignore()


def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError):
            pass

    app = QApplication(sys.argv)
    load_config()
    app.setQuitOnLastWindowClosed(False)
    w = FloatingButton()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()