# 悬浮按钮模块
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QPushButton, QMenu, QSystemTrayIcon, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QPoint, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QCursor, QGuiApplication, QAction
from .config_manager import config_manager
from .action_panel import ActionPanel

class FloatingButton(QWidget):
    """主悬浮按钮"""
    
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.action_panel: Optional[ActionPanel] = None
        self._drag_pos: Optional[QPoint] = None
        self._mouse_press_pos: Optional[QPoint] = None
        self._is_dragging = False
        
        self.setup_ui()
        self.setup_tray()
        self.setup_timers()
        
        # 移动到屏幕右侧中间
        self.move_to_right_middle()
        
    def setup_ui(self):
        """设置用户界面"""
        fb_config = config_manager.get("floating_button", {})
        size = fb_config.get("size", 60)
        style_config = fb_config.get("style", {})
        
        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(size, size)
        
        # 创建按钮
        self.button = QPushButton("Q", self)
        self.button.setGeometry(0, 0, size, size)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 设置按钮样式
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
            QPushButton:pressed {{
                background: #3b5ed6;
            }}
        """)
        
        # 设置透明度
        self.idle_opacity = fb_config.get("idle_opacity", 0.6)
        self.active_opacity = fb_config.get("active_opacity", 1.0)
        self.setWindowOpacity(self.idle_opacity)
        
        # 连接信号
        self.button.clicked.connect(self.toggle_panel)
        
        # 设置右键菜单
        self.setup_context_menu()
        
        # 安装事件过滤器
        self.button.installEventFilter(self)
        
        # 设置鼠标事件
        self.button.mousePressEvent = self.button_mousePressEvent
        self.button.mouseMoveEvent = self.button_mouseMoveEvent
        self.button.mouseReleaseEvent = self.button_mouseReleaseEvent
        
    def setup_context_menu(self):
        """设置右键菜单"""
        self.menu = QMenu()
        
        # 关于动作
        act_about = QAction("关于", self)
        act_about.triggered.connect(self.show_about)
        
        # 开机自启动作（占位）
        act_autostart = QAction("开机自启（占位）", self)
        act_autostart.setCheckable(True)
        
        # 退出动作
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_application)
        
        self.menu.addActions([act_about, act_autostart, act_quit])
        
        # 设置右键菜单策略
        self.button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.button.customContextMenuRequested.connect(
            lambda: self.menu.exec(self.mapToGlobal(QPoint(self.width() // 2, self.height())))
        )
        
    def setup_tray(self):
        """设置系统托盘"""
        self.tray = QSystemTrayIcon(self)
        # 使用项目内的SVG图标而不是系统主题图标，避免libpng警告
        from .icon_manager import icon_manager
        tray_icon = icon_manager.get_icon("grid")
        if not tray_icon.isNull():
            self.tray.setIcon(tray_icon)
        self.tray.setToolTip("Floating Quick Button")
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        
    def setup_timers(self):
        """设置定时器"""
        fb_config = config_manager.get("floating_button", {})
        
        # 边缘吸附设置
        self.snap_margin = fb_config.get("snap_margin", 10)
        self.edge_auto_snap = True
        
        # 保护定时器，确保按钮在屏幕内
        self.guard = QTimer(self)
        self.guard.timeout.connect(self.ensure_in_screen)
        self.guard.start(2500)
        
        # 跟踪前台窗口
        self.last_foreground_window = None
        self.last_foreground_timer = QTimer(self)
        self.last_foreground_timer.timeout.connect(self.update_last_foreground_window)
        self.last_foreground_timer.start(500)
        
    def move_to_right_middle(self):
        """将按钮移动到屏幕右侧中间位置"""
        geo = self.normalized_screen_geo()
        x = geo.right() - self.width() - 12
        y = geo.top() + (geo.height() - self.height()) // 2
        self.move(x, y)
        
    def normalized_screen_geo(self):
        """获取当前屏幕的可用几何区域"""
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()
        
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
            if nearest == d_left:
                x = geo.left()
            elif nearest == d_right:
                x = geo.right() - w
            elif nearest == d_top:
                y = geo.top()
            elif nearest == d_bottom:
                y = geo.bottom() - h
            self.move(x, y)
            
    def update_last_foreground_window(self):
        """更新最后的前台窗口"""
        # Windows平台特定代码
        import sys
        if sys.platform == "win32":
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                
                # 排除自己和动作面板的窗口
                exclude_hwnds = [int(self.winId())]
                if self.action_panel:
                    exclude_hwnds.append(int(self.action_panel.winId()))
                
                # 排除所有的应用内对话框（根据窗口标题判断）
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
                
                # 检查是否是应用内的对话框
                is_app_dialog = any(title in window_title for title in app_dialog_titles)
                
                if (hwnd not in exclude_hwnds and 
                    win32gui.IsWindowVisible(hwnd) and 
                    window_title != "" and
                    not is_app_dialog):
                    self.last_foreground_window = hwnd
                    # print(f"[DEBUG] 更新前台窗口: {window_title} (hwnd: {hwnd})")
            except Exception:
                pass
                
    def quit_application(self):
        """退出应用程序"""
        app = QApplication.instance()
        if app:
            app.quit()
            
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.information(
            self, "关于", 
            "这是一个悬浮按钮程序，样式类似 Quicker。\\n"
            "支持自定义动作、图标和快捷键。\\n"
            "版本：2.0"
        )
        
    @Slot()
    def toggle_panel(self):
        """切换面板显示状态"""
        print("[DEBUG] toggle_panel 被调用")
        
        # 关闭所有子面板，只保留主面板
        for panel in list(ActionPanel._open_panels):
            if panel._panel_id != "main_panel":
                panel.hide()
                panel.deleteLater()
                print(f"[DEBUG] 已关闭子面板: {panel._panel_id}")
                
        # 创建或显示主面板
        if self.action_panel is None:
            print("[DEBUG] 创建新的ActionPanel")
            self.action_panel = ActionPanel(parent=self)
            
        if self.action_panel.isVisible():
            print("[DEBUG] 隐藏面板")
            self.action_panel.hide()
        else:
            print("[DEBUG] 显示面板")
            self._position_panel()
            self.action_panel.show()
            self.action_panel.raise_()
            self.action_panel.activateWindow()
            
    def _position_panel(self):
        """定位面板位置"""
        if not self.action_panel:
            return
            
        btn_geo = self.geometry()
        panel_size = self.action_panel.size()
        screen_geo = self.normalized_screen_geo()
        
        # 默认在右侧显示
        pos_x = btn_geo.right() + 10
        pos_y = btn_geo.center().y() - panel_size.height() // 2
        
        # 如果右侧空间不够，在左侧显示
        if pos_x + panel_size.width() > screen_geo.right():
            pos_x = btn_geo.left() - panel_size.width() - 10
            
        # 确保Y坐标在屏幕范围内
        pos_y = max(screen_geo.top(), 
                   min(pos_y, screen_geo.bottom() - panel_size.height()))
                   
        self.action_panel.move(pos_x, pos_y)
        
    def button_mousePressEvent(self, event):
        """按钮鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._mouse_press_pos = event.globalPosition().toPoint()
            self._is_dragging = False
            
    def button_mouseMoveEvent(self, event):
        """按钮鼠标移动事件"""
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if (not self._is_dragging and 
                (event.globalPosition().toPoint() - self._mouse_press_pos).manhattanLength() > 10):
                self._is_dragging = True
                
            if self._is_dragging:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                
    def button_mouseReleaseEvent(self, event):
        """按钮鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                if self.edge_auto_snap:
                    self.snap_to_edges()
                self._is_dragging = False
            else:
                # 只有在没有拖拽时才触发点击
                self.toggle_panel()
                
            self._drag_pos = None
            self._mouse_press_pos = None
            
    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self.button:
            if event.type() == event.Type.Enter:
                self.setWindowOpacity(self.active_opacity)
            elif event.type() == event.Type.Leave:
                self.setWindowOpacity(self.idle_opacity)
                
        return super().eventFilter(obj, event)