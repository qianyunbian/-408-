# 图标管理模块
from typing import Optional, Dict, Any
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize, Qt

class IconManager:
    """图标管理器"""
    
    def __init__(self, svg_dir: str = "svg"):
        self.svg_dir = Path(svg_dir)
        self._icon_cache: Dict[str, QIcon] = {}
        self.default_size = QSize(24, 24)
        
        # 确保SVG目录存在
        self.svg_dir.mkdir(exist_ok=True)
    
    def get_icon(self, icon_name: str, size: Optional[QSize] = None) -> QIcon:
        """获取图标"""
        if not icon_name:
            return QIcon()
        
        # 检查缓存
        cache_key = f"{icon_name}_{size.width() if size else 24}x{size.height() if size else 24}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        # 查找SVG文件
        svg_path = self.svg_dir / f"{icon_name}.svg"
        if not svg_path.exists():
            svg_path = self.svg_dir / icon_name  # 如果已包含扩展名
        
        if not svg_path.exists():
            print(f"图标文件不存在: {svg_path}")
            return QIcon()
        
        try:
            # 创建图标
            icon = self._create_svg_icon(str(svg_path), size or self.default_size)
            self._icon_cache[cache_key] = icon
            return icon
        except Exception as e:
            print(f"加载图标失败 {svg_path}: {e}")
            return QIcon()
    
    def _create_svg_icon(self, svg_path: str, size: QSize) -> QIcon:
        """从SVG文件创建图标"""
        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            return QIcon()
        
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    def get_available_icons(self) -> list:
        """获取可用图标列表"""
        if not self.svg_dir.exists():
            return []
        
        icons = []
        for svg_file in self.svg_dir.glob("*.svg"):
            icons.append(svg_file.stem)  # 不包含扩展名
        
        return sorted(icons)
    
    def has_icon(self, icon_name: str) -> bool:
        """检查图标是否存在"""
        svg_path = self.svg_dir / f"{icon_name}.svg"
        if not svg_path.exists():
            svg_path = self.svg_dir / icon_name
        return svg_path.exists()
    
    def clear_cache(self):
        """清空图标缓存"""
        self._icon_cache.clear()

# 全局图标管理器实例
icon_manager = IconManager()