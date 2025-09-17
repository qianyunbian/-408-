import sys
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Any

# 添加src目录到Python路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon
except ImportError:
    print("错误：无法导入PySide6库。请安装：pip install PySide6")
    sys.exit(1)

# 导入应用模块
from src.config_manager import config_manager
from src.floating_button import FloatingButton
from src.action_panel import ActionPanel

class QuickerApp:
    """Quicker应用程序主类"""
    
    def __init__(self):
        self.app = None
        self.floating_button: Optional[FloatingButton] = None
        self.hotkey_manager: Optional[Any] = None
        
    def create_app(self):
        """创建QApplication实例"""
        app = QApplication(sys.argv)
            
        # 设置应用程序信息
        app.setApplicationName("Quicker")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("Quicker")
        app.setOrganizationDomain("quicker.local")
        
        # 设置应用图标
        try:
            icon_path = project_root / "svg" / "grid.svg"
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
            
        return app
        
    def init_hotkey_manager(self):
        """初始化热键管理器"""
        if not self.floating_button:
            print("热键管理器初始化失败：浮动按钮未初始化")
            return False
            
        try:
            from src.hotkey_manager import HotkeyManager
            
            self.hotkey_manager = HotkeyManager(self.floating_button)
            hotkey = config_manager.get("hotkeys.toggle_panel", "ctrl+alt+q")
            return self.hotkey_manager.register_hotkey(hotkey)
            
        except ImportError as e:
            print(f"热键管理器模块导入失败: {e}")
            print("⚠️ keyboard库不可用，全局热键功能将被禁用")
            print("   如需使用热键功能，请安装：pip install keyboard")
            return False
        except Exception as e:
            print(f"热键管理器初始化失败: {e}")
            return False
            
    def check_dependencies(self) -> bool:
        """检查依赖"""
        missing_deps = []
        
        # 检查PySide6
        try:
            import PySide6
        except ImportError:
            missing_deps.append("PySide6")
            
        # 检查可选依赖
        optional_deps = []
        
        try:
            import keyboard
        except ImportError:
            optional_deps.append("keyboard (用于全局热键)")
            
        try:
            import pyautogui
        except ImportError:
            optional_deps.append("pyautogui (用于模拟按键)")
            
        if sys.platform == "win32":
            try:
                import win32gui
            except ImportError:
                optional_deps.append("pywin32 (用于Windows功能)")
                
        if missing_deps:
            print("错误：缺少必需依赖：")
            for dep in missing_deps:
                print(f"  - {dep}")
            print("\\n请使用以下命令安装：")
            print(f"pip install {' '.join(missing_deps)}")
            return False
            
        if optional_deps:
            print("提示：以下可选依赖未安装：")
            for dep in optional_deps:
                print(f"  - {dep}")
            print()
            
        return True
        
    def setup_directories(self):
        """设置必要的目录"""
        # 确保SVG目录存在
        svg_dir = project_root / "svg"
        svg_dir.mkdir(exist_ok=True)
        
        # 确保配置文件存在
        config_file = project_root / "config.json"
        if not config_file.exists():
            print("创建默认配置文件...")
            config_manager.save_config()
            
    def run(self):
        """运行应用程序"""
        print("=" * 50)
        print("Quicker - 悬浮快捷按钮工具 v2.0")
        print("=" * 50)
        
        # 检查依赖
        if not self.check_dependencies():
            return 1
            
        # 设置目录
        self.setup_directories()
        
        # 创建应用
        self.app = self.create_app()
        
        # 检查是否已有实例运行
        try:
            existing_widgets = self.app.topLevelWidgets() if self.app else []
            if len(existing_widgets) > 0:
                QMessageBox.warning(
                    None, "警告", 
                    "Quicker可能已在运行中！\\n请检查系统托盘。"
                )
        except Exception:
            pass
            
        try:
            # 创建悬浮按钮
            print("初始化悬浮按钮...")
            self.floating_button = FloatingButton()
            self.floating_button.show()
            
            # 初始化热键管理器
            print("初始化热键管理器...")
            self.init_hotkey_manager()
            
            print("\\n✅ Quicker启动成功！")
            print("💡 使用提示：")
            print("   - 点击悬浮按钮打开动作面板")
            print("   - 右键点击按钮查看菜单")
            if self.hotkey_manager and hasattr(self.hotkey_manager, 'registered') and self.hotkey_manager.registered:
                hotkey = config_manager.get("hotkeys.toggle_panel", "ctrl+alt+q")
                print(f"   - 按 {hotkey} 快速切换面板")
            print("   - 在动作面板中右键按钮可重命名和修改图标")
            print()
            
            # 运行应用
            if self.app:
                return self.app.exec()
            return 1
            
        except KeyboardInterrupt:
            print("\\n程序被用户中断")
            return 0
        except Exception as e:
            print(f"\\n❌ 程序运行出错: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.cleanup()
            
    def cleanup(self):
        """清理资源"""
        print("\\n清理资源...")
        
        # 注销热键
        if self.hotkey_manager and hasattr(self.hotkey_manager, 'unregister_hotkey'):
            self.hotkey_manager.unregister_hotkey()
            
        # 保存配置（只在退出时强制保存）
        try:
            config_manager.save_config(force=True)
        except Exception as e:
            print(f"保存配置失败: {e}")
            
        print("✅ 清理完成")

def main():
    """主函数"""
    app = QuickerApp()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())