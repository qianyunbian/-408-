import sys
import json
import subprocess
import glob
import os
try:
    import pyautogui
except ImportError:
    pyautogui = None

# 导入 keyboard 库用于全局热键
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    keyboard = None
    KEYBOARD_AVAILABLE = False

# 导入 win32gui 和 win32con
if sys.platform == "win32":
    try:
        import win32gui
        import win32con
        import win32api
        import ctypes
        import ctypes.wintypes
    except ImportError:
        win32gui = None
        win32con = None
        win32api = None
        ctypes = None
        # 确保只有在ctypes不为None时才尝试访问wintypes
        if ctypes is not None:
            ctypes.wintypes = None
        else:
            # 创建一个模拟的wintypes模块，避免AttributeError
            import types
            ctypes_wintypes_mock = types.ModuleType('wintypes')
            if ctypes is None:
                ctypes = types.ModuleType('ctypes')
            ctypes.wintypes = ctypes_wintypes_mock
else:
    win32gui = None
    win32con = None
    win32api = None
    ctypes = None
    # 同样处理非Windows平台
    import types
    ctypes_wintypes_mock = types.ModuleType('wintypes')
    if ctypes is None:
        ctypes = types.ModuleType('ctypes')
    ctypes.wintypes = ctypes_wintypes_mock

from PySide6.QtGui import QAction, QGuiApplication, QIcon, QCursor, QDrag, QPixmap, QClipboard, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QPoint, QTimer, QRect, QMimeData, QEventLoop, QThread, QAbstractNativeEventFilter, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QMenu,
    QSystemTrayIcon, QMessageBox, QGridLayout, QLabel, QVBoxLayout,
    QInputDialog
)
from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtCore import Slot

CONFIG = {}

class DraggableButton(QPushButton):
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
                padding: 4px;
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
        if e.button() == Qt.LeftButton:
            self.start_pos = e.position().toPoint()
            self._is_dragging = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton):
            return
        if (e.position().toPoint() - self.start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        panel = self.parent()
        if not panel:
            return

        self._is_dragging = True
        panel._dragged_button = self  # 通知父面板：正在拖动这个按钮
        # 可选：高亮效果
        self.setStyleSheet(self.styleSheet() + "border: 2px dashed #4f7cff;")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._is_dragging:
            panel = self.parent()
            if panel:
                pos_in_panel = panel.mapFromGlobal(e.globalPosition().toPoint())
                target_index = panel.get_grid_index(pos_in_panel)

                try:
                    source_index = panel.buttons.index(self)
                    if 0 <= target_index < len(panel.buttons) and target_index != source_index:
                        # --- 互换模式 ---
                        panel.buttons[source_index], panel.buttons[target_index] = \
                            panel.buttons[target_index], panel.buttons[source_index]
                        panel.actions[source_index], panel.actions[target_index] = \
                            panel.actions[target_index], panel.actions[source_index]

                        panel._relayout_buttons()
                        panel.update_config_hierarchy()
                except ValueError:
                    pass

            # 恢复原样式
            self.setStyleSheet(self.styleSheet().replace("border: 2px dashed #4f7cff;", ""))
            self._is_dragging = False

        super().mouseReleaseEvent(e)

def mouseReleaseEvent(self, e):
    if e.button() == Qt.LeftButton and self._is_dragging:
        panel = self.parent()
        if panel:
            pos_in_panel = panel.mapFromGlobal(e.globalPosition().toPoint())
            target_index = panel.get_grid_index(pos_in_panel)

            try:
                source_index = panel.buttons.index(self)
                if 0 <= target_index < len(panel.buttons) and target_index != source_index:
                    # --- 互换模式 ---
                    panel.buttons[source_index], panel.buttons[target_index] = \
                        panel.buttons[target_index], panel.buttons[source_index]
                    panel.actions[source_index], panel.actions[target_index] = \
                        panel.actions[target_index], panel.actions[source_index]
                    panel._relayout_buttons()
                    panel.update_config_hierarchy()
            except ValueError:
                pass

        self.setWindowOpacity(1.0)
        self._is_dragging = False

    super().mouseReleaseEvent(e)

class ActionPanel(QWidget):
    """动作面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.buttons = []
        self._dragged_button = None
        self._drag_pos = None
        self._mouse_press_pos = None
        self._is_dragging = False
        self.edge_auto_snap = True

        self.last_foreground_timer = QTimer(self)
        self.last_foreground_timer.timeout.connect(self.check_last_foreground)
        self.last_foreground_timer.start(500)  # 每 500ms 检查一次

        # 初始化后恢复面板状态
        # This needs to be called AFTER the main event loop starts and window is shown
        # QTimer.singleShot(100, self._restore_panel_state) # Moved to main() after app.exec()

    def check_last_foreground(self):
        """检查是否为最后一个前台窗口"""
        if self.action_panel:
            # 检查窗口层级和焦点状态
            print(f"[DEBUG] 面板是否为活动窗口: {self.action_panel.isActiveWindow()}")
            print(f"[DEBUG] 面板是否为前台窗口: {QGuiApplication.focusWindow() == self.action_panel.windowHandle() if self.action_panel.windowHandle() else 'No window handle'}")
            
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

    def _on_drag_end(self):
        """当拖拽结束时调用"""
        # 通知所有打开的面板拖拽已结束
        for panel in ActionPanel._open_panels:
            panel._dragged_button = None

        if self.isHidden():
            self.show()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._is_dragging:
            panel = self.parent()
            if panel:
                target_index = panel.get_grid_index(e.position().toPoint())
                try:
                    source_index = panel.buttons.index(self)
                    # 移除并插入
                    btn = panel.buttons.pop(source_index)
                    act = panel.actions.pop(source_index)
                    if target_index > source_index:
                        target_index -= 1
                    panel.buttons.insert(target_index, btn)
                    panel.actions.insert(target_index, act)
                    panel._relayout_buttons()
                    panel.update_config_hierarchy()
                except ValueError:
                    pass
            self.setWindowOpacity(1.0)
            self._is_dragging = False
        super().mouseReleaseEvent(e)



class KeyboardHotkeyManager:
    """使用keyboard库实现的全局热键管理器（跨平台）"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.registered = False
        
    def register_hotkey(self):
        """注册全局热键"""
        if not KEYBOARD_AVAILABLE:
            print("keyboard库不可用，无法注册全局热键")
            return False
            
        try:
            # 注册全局热键 Ctrl+Alt+Q
            keyboard.add_hotkey('ctrl+alt+q', self._toggle_panel)
            self.registered = True
            print("✅ Keyboard全局热键注册成功: Ctrl+Alt+Q")
            return True
        except Exception as e:
            print(f"❌ Keyboard全局热键注册失败: {e}")
            return False
    
    def unregister_hotkey(self):
        """注销全局热键"""
        if self.registered and KEYBOARD_AVAILABLE:
            try:
                keyboard.remove_hotkey('ctrl+alt+q')
                self.registered = False
                print("Keyboard全局热键已注销")
            except Exception as e:
                print(f"注销Keyboard热键失败: {e}")
    
    def _toggle_panel(self):
        """切换面板显示状态（线程安全）"""
        if isinstance(self.main_window, FloatingButton):
            print(f"通过Keyboard热键调用 toggle_panel，FloatingButton实例: {self.main_window}")
            # 用 Qt 的事件队列在主线程里执行
            QMetaObject.invokeMethod(
                self.main_window,
                "toggle_panel",
                Qt.QueuedConnection
            )
        else:
            print("❌ main_window 不是 FloatingButton 实例或为 None，无法调用 toggle_panel")
        print("[DEBUG] 热键触发 -> toggle_panel()")


class ActionPanel(QWidget):
    """快捷功能面板"""
    # 用于保存面板状态的类变量
    _panel_states = {}
    # 用于跟踪当前打开的面板
    _open_panels = []
    
    def _generate_panel_id(self):
        """生成面板唯一标识符"""
        if isinstance(self.parent(), FloatingButton):
            return f"main_panel"
        elif isinstance(self.parent(), ActionPanel):
            # 基于父面板和在父面板中的位置生成ID
            parent_id = self.parent()._panel_id
            # 找到在父面板中的索引
            try:
                index = self.parent().sub_panels.index(self) if self in self.parent().sub_panels else len(self.parent().sub_panels)
            except:
                index = 0
            return f"{parent_id}_sub_{index}"
        else:
            return f"panel_{id(self)}"
    
    def __init__(self, parent=None, actions=None, level=0):
        super().__init__(parent)
        print(f"[DEBUG] ActionPanel.__init__ 调用, parent={parent}, level={level}")
        self._dragged_button = None
        self._current_placeholder_index = -1
        self.level = level
        self.actions = actions if actions is not None else CONFIG.get("actions", [])
        self.parent_panel = parent if isinstance(parent, ActionPanel) else None
        self.previous_active_window = None # 用于存储"最后的非自己窗口"句柄
        self._current_right_click_button = None  # 用于跟踪当前右键点击的按钮
        self.sub_panels = []  # 用于跟踪子面板实例

        # 生成面板唯一标识符
        self._panel_id = self._generate_panel_id()
        print(f"[DEBUG] 生成面板ID: {self._panel_id}")
        
        # 尝试恢复面板状态
        self._restore_state()

        panel_config = CONFIG.get("action_panel", {})
        btn_config = CONFIG.get("action_buttons", {})

        # 设置窗口标志以确保面板正确显示和激活
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        print(f"[DEBUG] 设置窗口标志: {self.windowFlags()}")
        # 检查各个标志位
        flags = self.windowFlags()
        print(f"[DEBUG] FramelessWindowHint: {bool(flags & Qt.FramelessWindowHint)}")
        print(f"[DEBUG] WindowStaysOnTopHint: {bool(flags & Qt.WindowStaysOnTopHint)}")
        print(f"[DEBUG] Tool: {bool(flags & Qt.Tool)}")
        print(f"[DEBUG] Popup: {bool(flags & Qt.Popup)}")
        print(f"[DEBUG] WindowDoesNotAcceptFocus: {bool(flags & Qt.WindowDoesNotAcceptFocus)}")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {panel_config.get("background_color", "rgba(240, 240, 240, 0.95)")};
                border-radius: 10px;
                border: 1px solid #ccc;
            }}
        """)
        self.setFixedSize(panel_config.get("width", 300), panel_config.get("height", 375))
        print(f"[DEBUG] 设置面板尺寸: {self.size()}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("Quicker")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; border: none; background: transparent;")
        main_layout.addWidget(title_label)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(btn_config.get("spacing", 10))
        main_layout.addLayout(self.grid_layout)
        
        # 确保在任何层级（包括从配置文件恢复的层级）都显示返回按钮
        print(f"ActionPanel 初始化，level: {self.level}, parent_panel: {self.parent_panel}")
        if self.level > 0 or (self.parent_panel and not isinstance(self.parent_panel, FloatingButton)):
            print("创建返回按钮，因为 level > 0 或有父面板")
            back_button = QPushButton("返回")
            back_button.clicked.connect(self.go_back)
            main_layout.addWidget(back_button)
        else:
            print("不创建返回按钮，因为 level 为 0")

        main_layout.addStretch()

        self.setAcceptDrops(True)
        
        self.buttons = []
        self.drop_placeholder = QWidget()
        btn_size = btn_config.get("size", 60)
        self.drop_placeholder.setFixedSize(btn_size, btn_size)
        self.drop_placeholder.setStyleSheet("background-color: transparent; border: 2px dashed #999; border-radius: 8px;")

        self.load_actions()
        
        # 检查是否应该从配置中恢复打开状态
        self._restore_open_state()
        print(f"[DEBUG] ActionPanel 初始化完成")

    def _restore_state(self):
        """恢复面板状态"""
        if self._panel_id in ActionPanel._panel_states:
            state = ActionPanel._panel_states[self._panel_id]
            # 恢复面板位置
            if 'position' in state:
                self.move(state['position'])
            print(f"恢复面板 {self._panel_id} 的状态")

    def _save_state(self):
        """保存面板状态"""
        state = {}
        # 保存面板位置
        state['position'] = self.pos()
        ActionPanel._panel_states[self._panel_id] = state
        print(f"保存面板 {self._panel_id} 的状态")

    def _restore_open_state(self):
        """根据配置恢复面板打开状态"""
        if getattr(self, "_restoring", False):
            print("[DEBUG] 正在恢复，跳过重复 show()")
            return
        self._restoring = True

        if isinstance(self.parent(), FloatingButton) and self._panel_id == "main_panel":
            open_panels = CONFIG.get("open_panels", [])
            if open_panels and len(open_panels) > 0:
                QTimer.singleShot(100, self.show)

        self._restoring = False


    def move(self, *args):
        """重写move方法以保存位置状态"""
        super().move(*args)
        # 更新状态中的位置信息
        if hasattr(self, '_panel_id'):
            self._save_state()

    def show(self):
        """重写show方法以跟踪打开的面板"""
        print(f"[DEBUG] ActionPanel.show() 被调用，面板ID: {self._panel_id}")
        print(f"[DEBUG] 显示前是否可见: {self.isVisible()}")
        print(f"[DEBUG] 窗口标志: {self.windowFlags()}")
        print(f"[DEBUG] 窗口属性: WA_TranslucentBackground={self.testAttribute(Qt.WA_TranslucentBackground)}")
        super().show()
        print(f"[DEBUG] 显示后是否可见: {self.isVisible()}")
        self._track_open_panel()
        # 添加更多调试信息
        print(f"[DEBUG] 面板几何信息: {self.geometry()}")
        print(f"[DEBUG] 面板是否激活: {self.isActiveWindow()}")

    def hide(self):
        """重写hide方法以保存状态"""
        print(f"[DEBUG] ActionPanel.hide() 被调用，面板ID: {self._panel_id}")
        print(f"[DEBUG] 隐藏前是否可见: {self.isVisible()}")
        self._save_state()
        self._untrack_open_panel()
        super().hide()
        print(f"[DEBUG] 隐藏后是否可见: {self.isVisible()}")
        # 添加更多调试信息
        print(f"[DEBUG] 面板几何信息: {self.geometry()}")

    def _track_open_panel(self):
        """跟踪打开的面板"""
        if self not in ActionPanel._open_panels:
            ActionPanel._open_panels.append(self)
            self._save_open_panels_state()

    def _untrack_open_panel(self):
        """取消跟踪关闭的面板"""
        if self in ActionPanel._open_panels:
            ActionPanel._open_panels.remove(self)
            self._save_open_panels_state()

    def _save_open_panels_state(self):
        """保存打开面板的状态到配置"""
        open_panel_ids = [panel._panel_id for panel in ActionPanel._open_panels]
        CONFIG["Ÿ"] = open_panel_ids
        print(f"保存打开面板状态: {open_panel_ids}")

    def closeEvent(self, event):
        """重写closeEvent以保存状态"""
        self._save_state()
        self._untrack_open_panel()
        super().closeEvent(event)

    def go_back(self):
        print(f"执行返回操作，当前面板level: {self.level}，parent_panel: {self.parent_panel}")
        self._save_state()
        self.hide()
        
        if self.parent_panel:
            print("返回到父面板")
            # 恢复父面板的位置并显示
            if hasattr(self.parent_panel, '_panel_id') and self.parent_panel._panel_id in ActionPanel._panel_states:
                state = ActionPanel._panel_states[self.parent_panel._panel_id]
                if 'position' in state:
                    self.parent_panel.move(state['position'])
            self.parent_panel.show()
        else:
            print("未找到父面板，尝试查找FloatingButton")
            # 查找并显示主面板
            floating_buttons = [w for w in QApplication.topLevelWidgets() if isinstance(w, FloatingButton)]
            print(f"找到 {len(floating_buttons)} 个 FloatingButton 实例")
            
            if floating_buttons:
                floating_button = floating_buttons[0]
                print(f"使用FloatingButton: {floating_button}")
                
                if floating_button.action_panel is None:
                    print("创建新的主面板")
                    # 如果主面板不存在，创建一个新的主面板
                    floating_button.action_panel = ActionPanel(parent=floating_button)
                else:
                    print("显示现有主面板")
                    # 恢复主面板的位置
                    if hasattr(floating_button.action_panel, '_panel_id') and floating_button.action_panel._panel_id in ActionPanel._panel_states:
                        state = ActionPanel._panel_states[floating_button.action_panel._panel_id]
                        if 'position' in state:
                            floating_button.action_panel.move(state['position'])
                
                floating_button.action_panel.show()
            else:
                print("未找到FloatingButton实例")

    def load_actions(self):
        # 清除现有的子面板跟踪
        self.sub_panels = []
        
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
        menu.addAction("新建子页面", lambda: self.create_new_action("panel"))
        menu.exec(QCursor.pos())

    def create_new_action(self, action_type):
        print(f"在层级 {self.level} 的面板中创建新动作，动作类型: {action_type}")
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
        elif action_type == "panel":
            # 创建一个新的子页面动作
            text, ok = QInputDialog.getText(self, "新增子页面", "请输入子页面名称：")
            if not ok or not text.strip():
                return
            new_action = {
                "name": text.strip(), 
                "type": "panel", 
                "actions": []
            }
        else:
            return
            
        print(f"创建新动作: {new_action}")
        # 新增动作后立即生成新的配置文件（带时间戳），而不是覆盖旧的
        # 这样每次添加都会保留历史版本
        # self.save_config_to_file()  # 移除重复调用

        self.actions.append(new_action)
        print(f"添加动作到当前面板，当前动作列表: {self.actions}")
        # 保存到配置文件 - 需要更新整个配置树
        self.update_config_hierarchy()
        print(f"更新全局配置，当前全局配置: {CONFIG}")
        if self.save_config_to_file():
            self.load_actions()
        else:
            # 如果保存失败，移除刚添加的动作
            self.actions.pop()

    def update_config_hierarchy(self):
        """更新配置层级结构，确保保存完整的配置树"""
        print(f"更新配置层级结构，当前面板层级: {self.level}")
        
        # 获取根配置
        root_config = self.get_root_config()
        print(f"根配置: {root_config}")
        
        # 更新全局CONFIG
        CONFIG.update(root_config)

    def get_root_config(self):
        """获取包含完整层级结构的根配置"""
        # 找到根面板
        root_panel = self
        while root_panel.parent_panel and not isinstance(root_panel.parent_panel, FloatingButton):
            root_panel = root_panel.parent_panel
            
        # 构建完整的配置结构
        root_config = {
            "floating_button": CONFIG.get("floating_button", {}),
            "action_panel": CONFIG.get("action_panel", {}),
            "action_buttons": CONFIG.get("action_buttons", {}),
        }
        
        # 构建动作树
        root_config["actions"] = self.build_action_tree(root_panel)
        print(f"构建的动作树: {root_config['actions']}")
        return root_config

    def build_action_tree(self, panel):
        """递归构建动作树"""
        actions = []
        for i, action in enumerate(panel.actions):
            action_copy = action.copy()
            # 如果是面板类型的动作，需要递归构建子面板的动作树
            if action.get("type") == "panel":
                # Check if this panel has a corresponding sub_panel instance
                # This logic assumes a direct mapping between action index and sub_panel index
                # which might be fragile if sub_panels are not always created/ordered in sync.
                # A more robust solution might involve mapping sub_panels by their _panel_id or a unique action identifier.
                # For now, let's assume direct index mapping for simplicity.
                if hasattr(panel, 'sub_panels') and i < len(panel.sub_panels) and panel.sub_panels[i].level == panel.level + 1:
                    action_copy["actions"] = self.build_action_tree(panel.sub_panels[i])
                elif "actions" in action_copy: # If no live sub_panel, use existing actions from config
                    # This branch handles cases where sub_panels might not be instantiated yet,
                    # or if the action was loaded from config and not yet opened.
                    # It recursively builds the tree from the 'actions' key in the config.
                    action_copy["actions"] = [self.build_action_tree_from_dict(sub_act) for sub_act in action_copy["actions"]]
            actions.append(action_copy)
        return actions

    def build_action_tree_from_dict(self, action_dict):
        """Helper to build action tree from a dictionary (for existing config)"""
        action_copy = action_dict.copy()
        if action_copy.get("type") == "panel" and "actions" in action_copy:
            action_copy["actions"] = [self.build_action_tree_from_dict(sub_act) for sub_act in action_copy["actions"]]
        return action_copy

    def open_sub_panel(self, actions):
        if self.level >= 4:  # Max 5 levels (0 to 4)
            QMessageBox.warning(self, "提示", "已达到最大层级。")
            return

        # 查找是否已经有相同的子面板
        sub_panel = None
        # A more robust way to find existing sub-panels might be to iterate through
        # self.sub_panels and compare their 'actions' list or a unique ID derived from it.
        # For now, we'll create a new one if not found.
        
        # Create a new sub-panel
        sub_panel = ActionPanel(parent=self, actions=actions, level=self.level + 1)
        self.sub_panels.append(sub_panel) # Add to track
        print(f"创建新的子面板 {sub_panel._panel_id}")
        
        # Add sub_panel to tracking list
        if sub_panel not in ActionPanel._open_panels:
            ActionPanel._open_panels.append(sub_panel)
            print(f"新增子面板到跟踪列表: {sub_panel._panel_id}")
        
        sub_panel.move(self.pos())
        sub_panel.show()
        self.hide()

    def create_action_button(self, name, callback):
        button = DraggableButton(name, self)
        button.clicked.connect(callback)
        
        # 为按钮设置图标样式，特别是为panel类型的按钮设置特殊图标
        # 检查回调函数是否是打开子面板的函数
        # 对于lambda表达式，我们需要检查其默认参数来判断是否是面板类型
        icon = "🔘"  # 默认图标
        
        # Determine icon based on action type or callback function
        # This part is a bit tricky with lambdas. A more direct way is to pass the action_type itself.
        # For now, let's try to infer from the callback.
        
        # Infer type from callback arguments (for lambdas)
        if hasattr(callback, '__code__'):
            co_varnames = callback.__code__.co_varnames
            if 'sub_acts' in co_varnames: # This implies it's a panel action
                icon = "📁"
            elif 'cmd' in co_varnames and 'run_program' in str(callback): # Heuristic for program
                icon = "⚙️"
            elif 'cmd' in co_varnames and 'simulate_key' in str(callback): # Heuristic for key
                icon = "⌨️"
            elif 'url' in co_varnames and 'open_url' in str(callback): # Heuristic for URL
                icon = "🌐"
            elif 'txt' in co_varnames and 'send_text' in str(callback): # Heuristic for text
                icon = "📝"
            elif 'n' in co_varnames and 'show_placeholder' in str(callback): # Heuristic for placeholder
                icon = "🔄"
            elif 'cmd' in co_varnames and 'run_command' in str(callback): # Heuristic for command
                icon = "⚡"
        
        # Direct check for specific methods
        if callback == self.send_clipboard_with_parentheses:
            icon = "📋"
        elif hasattr(callback, '__self__') and callback.__self__ == self:
            # Check if it's one of the known methods of self
            if callback.__name__ == 'open_sub_panel':
                icon = "📁"
            elif callback.__name__ == 'run_program':
                icon = "⚙️"
            elif callback.__name__ == 'simulate_key':
                icon = "⌨️"
            elif callback.__name__ == 'open_url':
                icon = "🌐"
            elif callback.__name__ == 'send_text':
                icon = "📝"
            elif callback.__name__ == 'show_placeholder':
                icon = "🔄"
            elif callback.__name__ == 'run_command':
                icon = "⚡"

        # 设置按钮文本为图标+换行+原名称
        button.setText(f"{icon}\n{name}")
        button.setStyleSheet(button.styleSheet() + """
            QPushButton {
                font-family: "Segoe UI Emoji", "Arial";
                text-align: center;
            }
        """)
        
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

        try:
            source_index = self.buttons.index(self._dragged_button)
        except ValueError:
            source_index = -1

        target_index = self.get_grid_index(e.position().toPoint())

        if source_index != -1:
            # 删除原位置
            btn = self.buttons.pop(source_index)
            act = self.actions.pop(source_index)

            # 修正 target_index（因为删除后索引可能偏移）
            if target_index > source_index:
                target_index -= 1

            # 限制范围，防止越界
            target_index = max(0, min(target_index, len(self.buttons)))

            # 插入到目标位置
            self.buttons.insert(target_index, btn)
            self.actions.insert(target_index, act)

        self._relayout_buttons()
        self.update_config_hierarchy()
        # self.save_config_to_file()

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
                # If the dragged button was from another panel, it won't be in this panel's buttons.
                # This might need more complex handling if cross-panel dragging is intended.
                # For now, just ensure it shows up again if it was hidden.
                pass 
            self._dragged_button.show()
        
        # No need to call _relayout_buttons or save config if drag was cancelled
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
            # Ensure parent is FloatingButton and has last_foreground_window
            if isinstance(parent, FloatingButton):
                self.previous_active_window = getattr(parent, "last_foreground_window", None)
            else:
                self.previous_active_window = None # Or get current foreground if not from FloatingButton
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
                # Only attempt to switch if the window is valid and not minimized
                if win32gui.IsWindow(self.previous_active_window) and \
                   not win32gui.IsIconic(self.previous_active_window):
                    win32gui.SetForegroundWindow(self.previous_active_window)
                    QTimer.singleShot(200, lambda: self._perform_paste_and_restore_clipboard(original_text_to_restore))
                    return
            except Exception as e:
                print(f"Error switching to previous window: {e}")

        # Fallback if win32gui fails or window is invalid/minimized
        self._perform_paste_and_restore_clipboard(original_text_to_restore)

    def _perform_paste_and_restore_clipboard(self, original_text):
        """执行粘贴并恢复剪贴板"""
        try:
            pyautogui.hotkey('ctrl', 'v')
        except Exception as e:
            print(f"PyAutoGUI paste failed: {e}")
        finally:
            QTimer.singleShot(150, lambda: self._set_clipboard_text_with_retry(original_text))

    def _switch_to_previous_window(self):
        """切换到上一个活动窗口"""
        if win32gui and self.previous_active_window:
            try:
                # Check if the window handle is still valid
                if win32gui.IsWindow(self.previous_active_window):
                    # Restore if minimized
                    if win32gui.IsIconic(self.previous_active_window):
                        win32gui.ShowWindow(self.previous_active_window, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(self.previous_active_window)
                    return True
            except Exception as e:
                print(f"Error switching to previous window: {e}")
        return False

    def simulate_key(self, key_str):
        """模拟按键动作，支持输入序列、组合键、单个按键、文本串和延时等待"""
        if not pyautogui:
            QMessageBox.critical(self, "依赖缺失", "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
            return
        
        # 切换到上一个活动窗口
        self.hide() # Hide panel immediately
        QTimer.singleShot(100, lambda: self._switch_and_simulate(key_str))

    def _switch_and_simulate(self, key_str):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._simulate_key_action(key_str))
        else:
            # If switch failed, just simulate keys in current context
            self._simulate_key_action(key_str)

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
            
            # self.hide() # Already hidden earlier
        except Exception as e:
            QMessageBox.warning(self, "错误", f"模拟按键失败：{e}")

    def open_url(self, url):
        import webbrowser
        # 切换到上一个活动窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_open_url(url))

    def _switch_and_open_url(self, url):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._open_url_action(url))
        else:
            self._open_url_action(url)

    def _open_url_action(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
            # self.hide() # Already hidden earlier
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开网址：{e}")

    def send_text(self, text):
        if not pyautogui:
            QMessageBox.critical(self, "依赖缺失", "需要安装 'pyautogui' 库来执行此操作。\n请运行: pip install pyautogui")
            return
        # 切换到上一个活动窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_send_text(text))

    def _switch_and_send_text(self, text):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._send_text_action(text))
        else:
            self._send_text_action(text)

    def _send_text_action(self, text):
        try:
            pyautogui.write(text)
            # self.hide() # Already hidden earlier
        except Exception as e:
            QMessageBox.warning(self, "错误", f"发送文本失败：{e}")

    def run_program(self, program_path):
        # 切换到上一个活动窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_run_program(program_path))

    def _switch_and_run_program(self, program_path):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._run_program_action(program_path))
        else:
            self._run_program_action(program_path)

    def _run_program_action(self, program_path):
        try:
            subprocess.Popen(program_path)
            # self.hide() # Already hidden earlier
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动程序：{e}")

    def run_command(self, command, args=None):
        # 切换到上一个活动窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_run_command(command, args))

    def _switch_and_run_command(self, command, args):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._run_command_action(command, args))
        else:
            self._run_command_action(command, args)

    def _run_command_action(self, command, args=None):
        try:
            cmd_list = [command] + (args or [])
            subprocess.Popen(cmd_list)
            # self.hide() # Already hidden earlier
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法执行命令：{e}")

    def show_placeholder(self, feature_name):
        # 切换到上一个活动窗口
        self.hide()
        QTimer.singleShot(100, lambda: self._switch_and_show_placeholder(feature_name))

    def _switch_and_show_placeholder(self, feature_name):
        if self._switch_to_previous_window():
            QTimer.singleShot(200, lambda: self._show_placeholder_action(feature_name))
        else:
            self._show_placeholder_action(feature_name)

    def _show_placeholder_action(self, feature_name):
        QMessageBox.information(self, "提示", f"'{feature_name}' 功能尚未实现。")
        # self.hide() # Already hidden earlier

    def save_config_to_file(self, file_path="config"):
        """简化的配置文件保存功能，每次保存都生成新的配置文件"""
        import os
        import time
        
        print(f"开始保存配置文件，当前面板层级: {self.level}")
        # 生成带时间戳的新文件名
        timestamp = int(time.time())
        base_name = os.path.splitext(file_path)[0]
        extension = os.path.splitext(file_path)[1] if os.path.splitext(file_path)[1] else ""
        new_file_path = f"{base_name}_{timestamp}{extension}"
        
        # 更新配置中的打开面板状态
        open_panel_ids = [panel._panel_id for panel in ActionPanel._open_panels]
        CONFIG["open_panels"] = open_panel_ids
        print(f"保存时更新打开面板状态: {open_panel_ids}")
        
        print(f"正在保存配置到新文件: {new_file_path}")
        print(f"当前CONFIG内容: {CONFIG}")
        
        try:
            # Directly write to new file
            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(CONFIG, f, ensure_ascii=False, indent=2)
            
            # Validate save
            if os.path.exists(new_file_path) and os.path.getsize(new_file_path) > 0:
                print(f"配置保存成功: {new_file_path}")
                return True
            else:
                raise Exception("文件写入后验证失败")
                
        except Exception as e:
            print(f"配置保存失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存配置文件：{e}")
            return False

    def get_config_file_list(self):
        """获取所有配置文件列表"""
        import os
        import glob
        
        base_name = os.path.splitext("config")[0]
        # Ensure the pattern matches the generated files, e.g., config_*.json
        pattern = f"{base_name}_*.json" # Assuming JSON extension
        config_files = glob.glob(pattern)
        
        # Sort by timestamp in filename if possible, otherwise by modification time
        def get_timestamp_from_filename(filename):
            try:
                parts = os.path.basename(filename).split('_')
                if len(parts) > 1:
                    ts_str = parts[-1].split('.')[0]
                    return int(ts_str)
            except ValueError:
                pass
            return 0 # Fallback
        
        config_files.sort(key=lambda x: get_timestamp_from_filename(x), reverse=True)
        
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
            # Reload the global CONFIG object
            global CONFIG
            with open(selected_file, 'r', encoding='utf-8') as f:
                CONFIG = json.load(f)
            
            # Then reload actions for the current panel and all its sub-panels
            # This requires traversing the panel hierarchy or restarting the main window.
            # For simplicity, we'll just reload the main panel's actions.
            # A full application restart might be better for a complete config reload.
            QMessageBox.information(self, "成功", f"已加载配置文件: {os.path.basename(selected_file)}。可能需要重启应用以完全生效。")
            self.load_actions() # Reload actions for the current panel
            
            # If there's a main FloatingButton, tell it to re-initialize its panel
            # This is a bit hacky, a better way would be to pass a signal.
            app = QApplication.instance()
            floating_buttons = [w for w in app.topLevelWidgets() if isinstance(w, FloatingButton)]
            if floating_buttons:
                fb = floating_buttons[0]
                if fb.action_panel:
                    fb.action_panel.close() # Close existing panel
                    fb.action_panel = None # Clear reference
                # Re-create and show the main panel based on new config
                fb.action_panel = ActionPanel(parent=fb)
                fb.action_panel.show()

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
        menu.addAction("重新加载配置 (需重启)", self.reload_config_and_restart_prompt) # Changed
        menu.addAction("退出", QApplication.instance().quit) # Use app.quit directly
        menu.exec(QCursor.pos())

    def backup_config(self):
        """备份当前配置"""
        if self.save_config_to_file():
            QMessageBox.information(self, "备份成功", "配置已备份到新文件")
        else:
            QMessageBox.warning(self, "备份失败", "无法备份配置。")

    def reload_config_and_restart_prompt(self):
        """提示用户重新加载配置需要重启"""
        reply = QMessageBox.question(self, "重新加载配置", 
                                   "重新加载配置需要重启应用程序才能完全生效。是否现在重启？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # This is a simplified restart. In a real app, you might use a more robust restart mechanism.
            QApplication.instance().quit()
            # A more robust restart would involve launching a new process.
            # For this example, simply exiting and letting the user manually restart is sufficient.
            # Or, if running from a script, the script itself might restart it.
            # For now, just quit.
            print("应用程序将退出，请手动重新启动以加载新配置。")

    def validate_config(self):
        """验证配置文件是否有效 - This function is not used in menu anymore, but kept for completeness"""
        import json
        try:
            # Assuming 'config' is the latest config file.
            # A more robust validation would load the actual active config file.
            latest_config_file = self.get_config_file_list()
            if not latest_config_file:
                QMessageBox.warning(self, "验证失败", "没有找到任何配置文件。")
                return
            
            with open(latest_config_file[0], "r", encoding="utf-8") as f:
                json.load(f)
            QMessageBox.information(self, "验证成功", f"配置文件 '{os.path.basename(latest_config_file[0])}' 有效。")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.warning(self, "验证失败", f"配置文件无效：{e}")
        except Exception as e:
            QMessageBox.warning(self, "验证失败", f"验证过程中发生错误：{e}")

    def reload_config(self):
        """重新加载配置文件 - This function is not used directly from menu anymore"""
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
            
        # 添加重新加载配置选项
        reload_action = menu.addAction("重新加载配置")
        cancel_action = menu.addAction("取消")
        print("Menu created with available actions")
        
        action = menu.exec(self.mapToGlobal(position))
        print(f"Menu executed, selected action: {action}")
        
        if self._current_right_click_button and action == delete_action:
            print("Delete action selected")
            self.delete_action(self._current_right_click_button)
        elif action == reload_action:
            print("Reload action selected")
            self.reload_config()
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
                removed_action = self.actions.pop(index)
                print(f"Action removed from panel.actions: {removed_action}")
                
                # 从按钮列表中移除按钮
                self.buttons.pop(index)
                
                # If the removed action was a panel, ensure its sub_panel instance is also cleaned up
                if removed_action.get("type") == "panel":
                    # Find the corresponding sub_panel instance and remove it from tracking
                    # This assumes a direct correspondence, which might need more robust handling
                    # if sub_panels are dynamically created/removed out of order.
                    # Iterate in reverse to safely remove items
                    for i in range(len(self.sub_panels) - 1, -1, -1):
                        sub_p = self.sub_panels[i]
                        # A more robust check would involve comparing content or a unique ID
                        # For now, if the sub_panel was at the same relative position, remove it.
                        # This is a weak heuristic and might need improvement.
                        if i == index:  # Simple index correspondence
                            if sub_p.isVisible():
                                sub_p.hide()
                            sub_p.deleteLater()
                            self.sub_panels.pop(i)
                            break

                # 更新配置并保存
                self.update_config_hierarchy()  # Rebuild the whole config tree
                print("CONFIG updated")
                if self.save_config_to_file():
                    print("Config saved successfully")
                    # 重新加载动作按钮
                    self.load_actions()
                    print("Actions reloaded")
                else:
                    # 如果保存失败，恢复动作
                    print("Failed to save config, attempting to restore action.")
                    self.actions.insert(index, removed_action)  # Restore the action if save failed
                    self.buttons.insert(index, button)  # Restore the button if save failed
                    self.load_actions()  # Reload to reflect restored state
        except (ValueError, IndexError) as e:
            print(f"Exception in delete_action: {e}")
            pass


class FloatingButton(QWidget):
    # 定义信号
    clicked = Signal()
    
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

        # 新增：持续记录"最后的非自己窗口"句柄
        self.last_foreground_window = None
        self.last_foreground_timer = QTimer(self)
        self.last_foreground_timer.timeout.connect(self.update_last_foreground_window)
        self.last_foreground_timer.start(500)  # 每 500ms 检查一次


        # 初始化后恢复面板状态
        # This needs to be called AFTER the main event loop starts and window is shown
        # QTimer.singleShot(100, self._restore_panel_state) # Moved to main() after app.exec()

    def move_to_right_middle(self):
        """将按钮移动到屏幕右侧中间位置"""
        geo = self.normalized_screen_geo()
        x = geo.right() - self.width() - 12
        y = geo.top() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def normalized_screen_geo(self):
        """获取当前屏幕的可用几何区域"""
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        return geo

    def ensure_in_screen(self):
        """确保按钮在屏幕范围内"""
        geo = self.normalized_screen_geo()
        x = min(max(self.x(), geo.left()), geo.right() - self.width())
        y = min(max(self.y(), geo.top()), geo.bottom() - self.height())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def snap_to_edges(self):
        """将按钮吸附到屏幕边缘"""
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

    def update_last_foreground_window(self):
        if win32gui:
            try:
                hwnd = win32gui.GetForegroundWindow()
                # Exclude self and other app windows (like the action panel)
                # Check if hwnd is a valid window and not our own app's window
                if hwnd != int(self.winId()) and \
                   (self.action_panel is None or hwnd != int(self.action_panel.winId())) and \
                   win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != "":
                    self.last_foreground_window = hwnd
            except Exception:
                pass

    def show_about(self):
        QMessageBox.information(self, "关于", "这是一个悬浮按钮程序示例，样式类似 Quicker。\n作者：Your Name\n版本：1.0")


    @Slot()
    def toggle_panel(self):

        # --- 新增：关闭所有子面板 ---
        for panel in list(ActionPanel._open_panels):
            if panel._panel_id != "main_panel":  # 保留主面板
                panel.hide()
                panel.deleteLater()
                print(f"[DEBUG] 已关闭子面板: {panel._panel_id}")

        if self.action_panel is None:
            print("[DEBUG] 尚未创建 ActionPanel，开始初始化...")
            self.action_panel = ActionPanel(parent=self)

        print(f"[DEBUG] 当前面板状态: 可见={self.action_panel.isVisible() if self.action_panel else 'None'}")
        if self.action_panel and self.action_panel.isVisible():
            print("[DEBUG] 面板已可见，准备隐藏")
            self.action_panel.hide()
            print(f"[DEBUG] 隐藏后面板状态: 可见={self.action_panel.isVisible()}")
        else:
            print("[DEBUG] 面板不可见，准备显示")
            if self.action_panel is None:
                print("[DEBUG] 面板实例为 None，重新创建")
                self.action_panel = ActionPanel(parent=self)

            # --- 保持原来的位置计算 ---
            btn_geo = self.geometry()
            panel_size = self.action_panel.size()
            screen_geo = self.normalized_screen_geo()

            pos_x = btn_geo.right() + 10
            pos_y = btn_geo.center().y() - panel_size.height() // 2

            if pos_x + panel_size.width() > screen_geo.right():
                pos_x = btn_geo.left() - panel_size.width() - 10

            pos_y = max(screen_geo.top(), min(pos_y, screen_geo.bottom() - panel_size.height()))

            self.action_panel.move(pos_x, pos_y)
            if not self.action_panel.isVisible():
                self.action_panel.show()
            else:
                print("[DEBUG] 主面板已可见，跳过 show()")

            # self.action_panel.show()
            self.action_panel.raise_()
            self.action_panel.activateWindow()

    def _restore_panel_state(self):
        """恢复面板状态"""
        try:
            # 检查配置中是否有需要恢复的面板状态
            open_panels = CONFIG.get("open_panels", [])
            if open_panels and len(open_panels) > 0:
                # 如果有需要恢复的面板，创建并显示主面板
                if self.action_panel is None:
                    self.action_panel = ActionPanel(parent=self)
                self.action_panel.show()
                print(f"恢复面板状态，打开的面板: {open_panels}")
        except Exception as e:
            print(f"恢复面板状态时出错: {e}")

    def on_click(self):
        """处理按钮点击事件"""
        self.toggle_panel()

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

    def _on_drag_end(self):
        """当拖拽结束时调用"""
        # 通知所有打开的面板拖拽已结束
        for panel in ActionPanel._open_panels:
            panel._dragged_button = None

        if self.isHidden():
            self.show()
            
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if not self._is_dragging:
                self.clicked.emit()
            self._is_dragging = False
        super().mouseReleaseEvent(e)


def load_config(config_dir="."):
    """加载最新的配置文件"""
    global CONFIG

    # 查找当前目录下所有 config_ 开头的文件
    config_files = glob.glob(os.path.join(config_dir, "config_*"))
    print(f"找到配置文件: {config_files}")
    if not config_files:
        msg = "未找到任何配置文件！"
        print(f"错误：{msg}")
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "配置错误", msg)
        sys.exit(1)

    # 按文件修改时间排序，取最新的
    latest_file = max(config_files, key=os.path.getmtime)
    print(f"选择最新的配置文件: {latest_file}")

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


if __name__ == "__main__":
    # 将main函数移到这里，确保所有类都已定义
    def main():
        global app
        app = QApplication(sys.argv)
        load_config()
        
        w = FloatingButton()
        w.show()
        
        # 尝试使用Windows原生API注册全局热键
        hotkey_manager = None
        if hotkey_manager is None:
            try:
                hotkey_manager = KeyboardHotkeyManager(w)
                if hotkey_manager.register_hotkey():
                    print("✅ Keyboard全局热键注册成功: Ctrl+Alt+Q")
                else:
                    print("❌ Keyboard全局热键注册失败")
                    hotkey_manager = None
            except Exception as e:
                print(f"Keyboard热键初始化异常: {e}")
                hotkey_manager = None

        # Restore panel state after the main event loop starts
        QTimer.singleShot(100, w._restore_panel_state)

        # Run the application
        sys.exit(app.exec())
    
    main()
