"""
服务管理器 - 智能端口分配和重复启动检测

功能：
1. 端口占用检测和自动分配
2. 服务状态记录
3. 服务存活检测
4. 避免重复启动
"""

import socket
import json
import os
import psutil
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import threading


class ServiceManager:
    """服务管理器"""

    def __init__(self, service_name: str = "wxauto-restful-api", config_path: str = "data"):
        """
        初始化服务管理器

        Args:
            service_name: 服务名称
            config_path: 配置文件目录
        """
        self.service_name = service_name
        self.config_path = Path(config_path)
        self.status_file = self.config_path / "service_status.json"
        self.lock_file = self.config_path / "service.lock"

        # 确保目录存在
        self.config_path.mkdir(parents=True, exist_ok=True)

    def check_port_available(self, port: int) -> bool:
        """
        检查端口是否可用

        Args:
            port: 端口号

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def find_available_port(self, start_port: int, max_attempts: int = 100) -> int:
        """
        查找可用端口

        Args:
            start_port: 起始端口
            max_attempts: 最大尝试次数

        Returns:
            可用的端口号
        """
        for offset in range(max_attempts):
            port = start_port + offset
            if self.check_port_available(port):
                return port

        raise RuntimeError(f"无法在 {start_port}-{start_port + max_attempts} 范围内找到可用端口")

    def is_process_running(self, pid: int) -> bool:
        """
        检查进程是否运行中

        Args:
            pid: 进程ID

        Returns:
            True if process is running, False otherwise
        """
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def is_service_healthy(self, port: int) -> bool:
        """
        检查服务是否健康

        Args:
            port: 服务端口

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/docs",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def save_service_status(self, port: int, pid: int, additional_info: Optional[Dict] = None):
        """
        保存服务状态

        Args:
            port: 服务端口
            pid: 进程ID
            additional_info: 额外信息
        """
        status = {
            "service_name": self.service_name,
            "port": port,
            "pid": pid,
            "start_time": datetime.now().isoformat(),
            "status": "running"
        }

        if additional_info:
            status.update(additional_info)

        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

    def load_service_status(self) -> Optional[Dict[str, Any]]:
        """
        加载服务状态

        Returns:
            服务状态字典，如果不存在则返回 None
        """
        if not self.status_file.exists():
            return None

        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def clear_service_status(self):
        """清除服务状态"""
        if self.status_file.exists():
            self.status_file.unlink()

    def get_running_service(self) -> Optional[Dict[str, Any]]:
        """
        获取正在运行的服务信息

        Returns:
            服务信息字典，如果没有运行中的服务则返回 None
        """
        status = self.load_service_status()
        if not status:
            return None

        # 检查进程是否还在运行
        if not self.is_process_running(status['pid']):
            # 进程已停止，清除状态
            self.clear_service_status()
            return None

        # 检查服务是否健康
        if not self.is_service_healthy(status['port']):
            # 服务不健康，清除状态
            self.clear_service_status()
            return None

        return status

    def acquire_lock(self) -> bool:
        """
        尝试获取启动锁

        Returns:
            True if lock acquired successfully, False otherwise
        """
        if self.lock_file.exists():
            # 检查锁是否过期（超过5分钟）
            try:
                lock_time = datetime.fromtimestamp(self.lock_file.stat().st_mtime)
                if (datetime.now() - lock_time).seconds < 300:
                    return False
            except:
                pass

        # 创建锁文件
        self.lock_file.touch()
        return True

    def release_lock(self):
        """释放启动锁"""
        if self.lock_file.exists():
            self.lock_file.unlink()

    def start_service(
        self,
        preferred_port: int,
        max_attempts: int = 100,
        force_restart: bool = False
    ) -> Dict[str, Any]:
        """
        启动服务（智能端口分配）

        Args:
            preferred_port: 首选端口
            max_attempts: 最大尝试次数
            force_restart: 是否强制重启

        Returns:
            服务信息字典
        """
        # 检查是否已有运行中的服务
        if not force_restart:
            running_service = self.get_running_service()
            if running_service:
                return {
                    "action": "use_existing",
                    "message": f"检测到服务已在运行中 (端口: {running_service['port']})",
                    "port": running_service['port'],
                    "pid": running_service['pid'],
                    "status": running_service
                }

        # 获取启动锁
        if not self.acquire_lock():
            return {
                "action": "lock_failed",
                "message": "无法获取启动锁，可能有其他进程正在启动服务",
                "port": None,
                "pid": None
            }

        try:
            # 查找可用端口
            available_port = self.find_available_port(preferred_port, max_attempts)

            return {
                "action": "start_new",
                "message": f"将在端口 {available_port} 启动服务" +
                          (f" (首选端口 {preferred_port} 已被占用)" if available_port != preferred_port else ""),
                "port": available_port,
                "pid": os.getpid(),
                "preferred_port": preferred_port
            }
        finally:
            # 启动完成后释放锁
            self.release_lock()

    def notify_service_started(self, port: int, additional_info: Optional[Dict] = None):
        """
        通知服务已启动

        Args:
            port: 服务端口
            additional_info: 额外信息
        """
        self.save_service_status(
            port=port,
            pid=os.getpid(),
            additional_info=additional_info
        )

    def stop_service(self):
        """停止服务"""
        self.clear_service_status()
        self.release_lock()

    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息

        Returns:
            服务信息字典
        """
        running_service = self.get_running_service()
        if running_service:
            return {
                "status": "running",
                "port": running_service['port'],
                "pid": running_service['pid'],
                "start_time": running_service.get('start_time'),
                "action": "existing"
            }
        else:
            return {
                "status": "not_running",
                "port": None,
                "pid": None,
                "action": "need_start"
            }


# 全局服务管理器实例
_service_manager = None
_manager_lock = threading.Lock()


def get_service_manager(service_name: str = "wxauto-restful-api") -> ServiceManager:
    """
    获取全局服务管理器实例

    Args:
        service_name: 服务名称

    Returns:
        ServiceManager 实例
    """
    global _service_manager

    if _service_manager is None:
        with _manager_lock:
            if _service_manager is None:
                _service_manager = ServiceManager(service_name)

    return _service_manager
