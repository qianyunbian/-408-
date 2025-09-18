# 热键管理模块
from typing import Optional, TYPE_CHECKING, Dict, Callable
from PySide6.QtCore import QObject, QMetaObject, Qt, QTimer, Signal
import threading

if TYPE_CHECKING:
    from .floating_button import FloatingButton

class HotkeySignalEmitter(QObject):
    """信号发射器，用于线程安全的信号发射"""
    toggle_requested = Signal()
    action_requested = Signal(str)  # 新增：动作执行信号，传递动作ID
    
    def __init__(self):
        super().__init__()

class HotkeyManager:
    """全局热键管理器（参照1.94.py实现）"""
    
    def __init__(self, floating_button: 'FloatingButton'):
        self.floating_button = floating_button
        self.registered = False
        self._lock = threading.Lock()  # 线程锁防止并发问题
        self._action_hotkeys: Dict[str, str] = {}  # 动作热键映射：hotkey -> action_id
        
        # 创建信号发射器并连接到toggle_panel
        self.signal_emitter = HotkeySignalEmitter()
        self.signal_emitter.toggle_requested.connect(self.floating_button.toggle_panel)
        self.signal_emitter.action_requested.connect(self._execute_action)
        
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
            
    def register_action_hotkeys(self, actions: list) -> None:
        """注册动作快捷键"""
        if not self.registered:
            return
            
        try:
            import keyboard
            
            # 清除之前的动作热键
            for hotkey in self._action_hotkeys.keys():
                try:
                    keyboard.remove_hotkey(hotkey)
                except:
                    pass
            self._action_hotkeys.clear()
            
            # 注册新的动作热键
            for action in actions:
                hotkey = action.get('hotkey', '').strip()
                action_id = action.get('id')
                
                if hotkey and action_id:
                    try:
                        keyboard.add_hotkey(hotkey, lambda aid=action_id: self._execute_action_by_id(aid))
                        self._action_hotkeys[hotkey] = action_id
                        print(f"✅ 动作快捷键注册成功: {action.get('name', '未命名')} -> {hotkey}")
                    except Exception as e:
                        print(f"❌ 动作快捷键注册失败 [{action.get('name', '未命名')}] {hotkey}: {e}")
                        
        except ImportError:
            print("⚠️ keyboard库不可用，动作快捷键功能将被禁用")
        except Exception as e:
            print(f"❌ 注册动作快捷键失败: {e}")
            
    def unregister_hotkey(self):
        """注销全局热键"""
        if self.registered:
            try:
                import keyboard
                keyboard.unhook_all()
                self.registered = False
                self._action_hotkeys.clear()
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
                
    def _execute_action_by_id(self, action_id: str):
        """通过动作ID执行动作（线程安全）"""
        with self._lock:
            print(f"[DEBUG] 动作热键触发 -> action_id: {action_id}")
            try:
                self.signal_emitter.action_requested.emit(action_id)
                print("[DEBUG] 动作信号发出成功")
            except Exception as e:
                print(f"发出动作信号失败: {e}")
                
    def _execute_action(self, action_id: str):
        """执行指定的动作"""
        if self.floating_button:
            try:
                # 获取或创建动作面板
                if not hasattr(self.floating_button, 'action_panel') or not self.floating_button.action_panel:
                    # 如果面板不存在，先显示面板再执行动作
                    self.floating_button.toggle_panel()  # 这会创建面板
                    # 等待面板创建完成后执行动作
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(100, lambda: self._delayed_execute_action(action_id))
                    return
                
                # 直接执行动作（不显示面板）
                panel = self.floating_button.action_panel
                if panel:
                    panel.execute_action_by_id(action_id)
                else:
                    print(f"❌ 动作面板创建失败，无法执行动作: {action_id}")
            except Exception as e:
                print(f"❌ 执行动作失败 [{action_id}]: {e}")
        else:
            print(f"❌ floating_button 为 None，无法执行动作: {action_id}")
            
    def _delayed_execute_action(self, action_id: str):
        """延迟执行动作（等待面板创建完成）"""
        try:
            if self.floating_button and self.floating_button.action_panel:
                self.floating_button.action_panel.execute_action_by_id(action_id)
            else:
                print(f"❌ 延迟执行失败，面板未创建: {action_id}")
        except Exception as e:
            print(f"❌ 延迟执行动作失败 [{action_id}]: {e}")