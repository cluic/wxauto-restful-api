"""
wxautox4 包管理器（简化版）

统一使用 wxautox4
"""

import importlib
from typing import Any, List
from app.utils.logger import setup_logger

logger = setup_logger()

class WxPackageManager:
    """wxautox4 包管理器（简化版）"""

    def __init__(self):
        """初始化包管理器"""
        self._package = None
        self._load_package()

    def _load_package(self) -> None:
        """加载 wxautox4 包"""
        try:
            self._package = importlib.import_module("wxautox4")
            logger.info("已加载 wxautox4 包")
        except ImportError as e:
            logger.error(f"无法导入 wxautox4 包: {e}")
            raise ImportError("请确保已安装 wxautox4 包: pip install wxautox4")

    @property
    def package(self) -> Any:
        """获取包对象"""
        return self._package

    def get_class(self, class_name: str) -> Any:
        """获取包中的类

        Args:
            class_name: 类名

        Returns:
            类对象
        """
        if hasattr(self._package, class_name):
            return getattr(self._package, class_name)
        else:
            raise AttributeError(f"wxautox4 包中没有 {class_name} 类")

    def get_function(self, function_name: str) -> Any:
        """获取包中的函数

        Args:
            function_name: 函数名

        Returns:
            函数对象
        """
        if hasattr(self._package, function_name):
            return getattr(self._package, function_name)
        else:
            raise AttributeError(f"wxautox4 包中没有 {function_name} 函数")

    def get_supported_features(self) -> List[str]:
        """获取当前包支持的功能列表

        Returns:
            支持的功能列表
        """
        return [
            "基础消息发送",
            "文件发送",
            "聊天窗口切换",
            "获取聊天信息",
            "获取子窗口",
            "获取消息",
            "URL卡片发送",
            "监听聊天",
            "获取新消息",
            "引用消息",
            "好友申请管理",
            "页面切换",
            "在线状态检查",
            "获取会话列表",
            "获取历史消息",
            "获取群聊列表",
            "✨创建群聊",
            "✨添加群成员",
            "✨修改群聊信息",
            "获取好友列表",
            "获取我的信息",
            "添加好友",
            "朋友圈功能",
            "高级参数配置",
            "日志系统"
        ]

# 全局包管理器实例
wx_manager = WxPackageManager()

# 便捷函数
def get_wx_class(class_name: str) -> Any:
    """获取wx类

    Args:
        class_name: 类名

    Returns:
        类对象
    """
    return wx_manager.get_class(class_name)

def get_wx_function(function_name: str) -> Any:
    """获取wx函数

    Args:
        function_name: 函数名

    Returns:
        函数对象
    """
    return wx_manager.get_function(function_name)

def get_supported_features() -> List[str]:
    """获取支持的功能列表"""
    return wx_manager.get_supported_features()
