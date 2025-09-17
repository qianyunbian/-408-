# 配置管理模块
import json
import os
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config_dir = self.config_file.parent
        self.svg_dir = self.config_dir / "svg"
        
        # 备份文件夹管理
        self.backup_dir = self.config_dir / "config_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backup_size_mb = 20  # 20MB限制
        
        # 输入输出动作文件夹管理
        self.input_output_dir = self.config_dir / "input_output_actions"
        self.input_output_dir.mkdir(exist_ok=True)
        
        self._config = self._load_default_config()
        self._original_config = None  # 用于检查配置是否有变化
        self._config_modified = False  # 配置修改标记
        self.load_config()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "floating_button": {
                "size": 60,
                "snap_margin": 10,
                "idle_opacity": 0.6,
                "active_opacity": 1.0,
                "style": {
                    "background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f7cff, stop:1 #6ce0ff)",
                    "hover_background": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #608cff, stop:1 #7cf0ff)",
                    "color": "white",
                    "font_size": 20,
                    "font_weight": 700
                }
            },
            "action_panel": {
                "width": 380,
                "height": 300,
                "columns": 4,
                "background_color": "rgba(240, 240, 240, 0.95)"
            },
            "action_buttons": {
                "size": 66,
                "spacing": 10,
                "style": {
                    "background_color": "#f8fbff",  # 与控制按钮一致的背景色
                    "border": "1px solid #ddd",
                    "border_radius": 12,
                    "font_size": 9,
                    "color": "#333",
                    "hover_background_color": "#e6f0ff",  # 与控制按钮一致的悬停背景色
                    "hover_border_color": "#4f7cff",
                    "pressed_background_color": "#e0f0ff"
                }
            },
            "hotkeys": {
                "toggle_panel": "ctrl+alt+q"
            },
            "actions": []
        }
    
    def load_config(self) -> None:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self._merge_config(saved_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        
        # 保存原始配置的副本，用于检查变化
        self._original_config = json.dumps(self._config, ensure_ascii=False, indent=2, sort_keys=True)
        self._config_modified = False
    
    def _merge_config(self, saved_config: Dict[str, Any]) -> None:
        """合并配置"""
        def deep_merge(base: Dict, update: Dict) -> Dict:
            result = base.copy()
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = deep_merge(self._config, saved_config)
    
    def _get_backup_files(self) -> List[Path]:
        """获取所有备份文件，按时间排序"""
        if not self.backup_dir.exists():
            return []
        
        backup_files = list(self.backup_dir.glob("config_backup_*.json"))
        # 按修改时间排序（旧的在前）
        backup_files.sort(key=lambda f: f.stat().st_mtime)
        return backup_files
    
    def _get_backup_size(self) -> int:
        """获取备份文件夹的总大小（字节）"""
        backup_files = self._get_backup_files()
        total_size = 0
        for file_path in backup_files:
            try:
                total_size += file_path.stat().st_size
            except OSError:
                continue
        return total_size
    
    def _cleanup_old_backups(self):
        """清理旧的备份文件，保持总大小在限制内"""
        max_size_bytes = self.max_backup_size_mb * 1024 * 1024  # 转换为字节
        
        while self._get_backup_size() > max_size_bytes:
            backup_files = self._get_backup_files()
            if not backup_files:
                break
                
            # 删除最旧的文件
            oldest_file = backup_files[0]
            try:
                oldest_file.unlink()
                print(f"已删除旧备份文件: {oldest_file.name}")
            except OSError as e:
                print(f"删除备份文件失败: {e}")
                break
    
    def _create_backup(self) -> Optional[Path]:
        """创建配置文件备份"""
        if not self.config_file.exists():
            return None
            
        try:
            # 创建备份文件名（带时间戳）
            backup_filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.backup_dir / backup_filename
            
            # 复制文件
            shutil.copy2(self.config_file, backup_path)
            print(f"配置文件已备份到: {backup_path}")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return backup_path
        except Exception as e:
            print(f"创建备份文件失败: {e}")
            return None
    
    def save_config(self, force: bool = False) -> bool:
        """保存配置文件（只在退出时或强制保存时执行）"""
        # 检查配置是否真正发生变化
        current_config = json.dumps(self._config, ensure_ascii=False, indent=2, sort_keys=True)
        if not force and self._original_config and self._original_config == current_config:
            print("配置未发生变化，无需保存")
            return True
            
        if not force and not self._config_modified:
            print("配置未修改，无需保存")
            return True
            
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(exist_ok=True)
            
            # 只在配置真正变化时才备份（使用新的备份系统）
            if self.config_file.exists() and self._original_config != current_config:
                self._create_backup()
            
            # 保存新配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            # 更新原始配置和修改标记
            self._original_config = current_config
            self._config_modified = False
            print(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._config_modified = True
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._merge_config(config)
        self._config_modified = True
    
    def create_action(self, name: str, action_type: str, **kwargs) -> Dict[str, Any]:
        """创建新动作配置"""
        import uuid
        action = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": action_type,
            "icon_path": kwargs.get("icon_path", ""),
            "hotkey": kwargs.get("hotkey", ""),
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        # 根据类型添加特定配置
        if action_type == "key":
            action["command"] = kwargs.get("command", "")
        elif action_type == "program":
            action["command"] = kwargs.get("command", "")
            action["args"] = kwargs.get("args", [])
        elif action_type == "url":
            action["url"] = kwargs.get("url", "")
        elif action_type == "text":
            action["text"] = kwargs.get("text", "")
        elif action_type == "panel":
            action["actions"] = kwargs.get("actions", [])
        elif action_type == "input_output":
            action["script_file"] = kwargs.get("script_file", "")
            action["input_source"] = kwargs.get("input_source", "clipboard")  # clipboard, selection, manual, none
            action["output_target"] = kwargs.get("output_target", "text")  # text, url, clipboard, file
            action["description"] = kwargs.get("description", "")
        elif action_type == "quick_send":
            action["filename"] = kwargs.get("filename", "")
            action["description"] = kwargs.get("description", "快捷发送文本内容")
        
        return action
    
    def get_svg_icons(self) -> list:
        """获取SVG图标列表"""
        if not self.svg_dir.exists():
            return []
        
        return [f.name for f in self.svg_dir.glob("*.svg")]
    
    def get_icon_path(self, icon_name: str) -> str:
        """获取图标完整路径"""
        if not icon_name:
            return ""
        
        icon_path = self.svg_dir / icon_name
        if icon_path.exists():
            return str(icon_path)
        
        return ""
    
    def get_backup_info(self) -> Dict[str, Any]:
        """获取备份信息"""
        backup_files = self._get_backup_files()
        total_size = self._get_backup_size()
        
        return {
            "backup_dir": str(self.backup_dir),
            "total_files": len(backup_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_backup_size_mb,
            "files": [
                {
                    "name": f.name,
                    "size_kb": round(f.stat().st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                }
                for f in backup_files
            ]
        }
    
    def set_backup_limit(self, max_size_mb: int):
        """设置备份文件夹大小限制"""
        if max_size_mb <= 0:
            raise ValueError("备份大小限制必须大于0")
        
        self.max_backup_size_mb = max_size_mb
        print(f"备份大小限制已设置为: {max_size_mb}MB")
        
        # 立即清理超出限制的文件
        self._cleanup_old_backups()
    
    def manual_cleanup_backups(self) -> int:
        """手动清理备份文件，返回清理的文件数量"""
        old_count = len(self._get_backup_files())
        self._cleanup_old_backups()
        new_count = len(self._get_backup_files())
        cleaned_count = old_count - new_count
        
        if cleaned_count > 0:
            print(f"已清理 {cleaned_count} 个老旧备份文件")
        else:
            print("没有需要清理的备份文件")
            
        return cleaned_count
        
    def load_backup_config(self, backup_path: Path) -> bool:
        """从备份文件加载配置"""
        try:
            if not backup_path.exists():
                print(f"备份文件不存在: {backup_path}")
                return False
                
            # 读取备份文件
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_config = json.load(f)
                
            # 验证配置格式
            if not isinstance(backup_config, dict):
                print("备份文件格式错误")
                return False
                
            # 保存当前配置作为备份
            self.save_config(force=True)
            
            # 更新配置
            self._config = backup_config
            self._original_config = json.dumps(self._config, ensure_ascii=False, indent=2, sort_keys=True)
            self._config_modified = False
            
            # 保存新配置到文件
            self.save_config(force=True)
            
            print(f"配置已从备份文件加载: {backup_path}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"备份文件JSON解析错误: {e}")
            return False
        except Exception as e:
            print(f"加载备份配置失败: {e}")
            return False
            
    def create_input_output_script(self, action_name: str, action_id: str, script_content: str) -> str:
        """创建输入输出动作脚本文件"""
        try:
            # 生成友好的文件名：动作名_短缩ID.py
            # 清理动作名：移除特殊字符，限制长度
            clean_name = self._clean_filename(action_name)
            short_id = action_id[:8]  # 只使用前8位作为短缩ID
            script_filename = f"{clean_name}_{short_id}.py"
            script_path = self.input_output_dir / script_filename
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            print(f"输入输出动作脚本已创建: {script_path}")
            return script_filename
            
        except Exception as e:
            print(f"创建输入输出动作脚本失败: {e}")
            return ""
            
    def _clean_filename(self, name: str) -> str:
        """清理文件名，移除不合法字符并限制长度"""
        import re
        # 移除或替换不合法的文件名字符
        clean_name = re.sub(r'[<>:"/\\|?*\s]+', '_', name)
        # 移除连续的下划线
        clean_name = re.sub(r'_+', '_', clean_name)
        # 移除开头和结尾的下划线
        clean_name = clean_name.strip('_')
        # 限制长度为15个字符
        if len(clean_name) > 15:
            clean_name = clean_name[:15]
        # 如果清理后为空，使用默认名称
        if not clean_name:
            clean_name = "action"
        return clean_name
            
    def get_input_output_script_path(self, script_filename: str) -> Path:
        """获取输入输出动作脚本的完整路径"""
        return self.input_output_dir / script_filename
        
    def delete_input_output_script(self, script_filename: str) -> bool:
        """删除输入输出动作脚本文件"""
        try:
            script_path = self.input_output_dir / script_filename
            if script_path.exists():
                script_path.unlink()
                print(f"输入输出动作脚本已删除: {script_path}")
                return True
            return False
        except Exception as e:
            print(f"删除输入输出动作脚本失败: {e}")
            return False
            
    def get_input_output_scripts(self) -> List[str]:
        """获取所有输入输出动作脚本文件列表"""
        if not self.input_output_dir.exists():
            return []
        # 支持新旧两种命名模式
        old_pattern_files = list(self.input_output_dir.glob("io_action_*.py"))
        new_pattern_files = list(self.input_output_dir.glob("*_[a-f0-9][a-f0-9][a-f0-9][a-f0-9][a-f0-9][a-f0-9][a-f0-9][a-f0-9].py"))
        all_files = old_pattern_files + new_pattern_files
        return [f.name for f in all_files]

# 全局配置管理器实例
config_manager = ConfigManager()