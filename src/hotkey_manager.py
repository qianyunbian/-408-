# 热键管理模块
from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import QObject, QMetaObject, Qt, QTimer, Signal
import threading

if TYPE_CHECKING:
    from .floating_button import FloatingButton

class HotkeySignalEmitter(QObject):
    """信号发射器，用于线程安全的信号发射"""
    toggle_requested = Signal()
    
    def __init__(self):
        super().__init__()

class HotkeyManager:
    """全局热键管理器（参照1.94.py实现）"""
    
    def __init__(self, floating_button: 'FloatingButton'):
        self.floating_button = floating_button
        self.registered = False
        self._lock = threading.Lock()  # 线程锁防止并发问题
        
        # 创建信号发射器并连接到toggle_panel
        self.signal_emitter = HotkeySignalEmitter()
        self.signal_emitter.toggle_requested.connect(self.floating_button.toggle_panel)
        
    def register_hotkey(self, hotkey: str = "ctrl+alt+q") -> bool:
        """注册全局热键"""
        try:
            import keyboard
            
            # 注册全局热键
            keyboard.add_hotkey(hotkey, self._toggle_panel)
            self.registered = True
            print(f"✅ 全局热键注册成功: {hotkey}")
            return True
            
        except ImportError:
            print("⚠️ keyboard库不可用，全局热键功能将被禁用")
            print("   如需使用热键功能，请安装：pip install keyboard")
            return False
        except Exception as e:
            print(f"❌ 全局热键注册失败: {e}")
            return False
            
    def unregister_hotkey(self):
        """注销全局热键"""
        if self.registered:
            try:
                import keyboard
                keyboard.unhook_all()
                self.registered = False
                print("全局热键已注销")
            except Exception as e:
                print(f"注销热键失败: {e}")
                
    def _toggle_panel(self):
        """切换面板显示状态（线程安全 - 使用信号机制）"""
        # 使用线程锁防止并发调用
        with self._lock:
            if self.floating_button:
                print("[DEBUG] 热键触发 -> toggle_panel()")
                # 使用信号机制（线程安全）
                try:
                    self.signal_emitter.toggle_requested.emit()
                    print("[DEBUG] 信号发出成功")
                except Exception as e:
                    print(f"发出信号失败: {e}")
            else:
                print("❌ floating_button 为 None，无法调用 toggle_panel")