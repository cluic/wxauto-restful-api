#!/usr/bin/env python3
"""
wxauto API 启动脚本
从配置文件读取服务器配置并启动服务

新增功能：
- 智能端口分配
- 重复启动检测
- 服务状态管理
"""

import sys
import uvicorn
import webbrowser
from pathlib import Path
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.services.service_manager import get_service_manager

# 延迟打开浏览器
def open_browser(url):
    import time
    time.sleep(2)
    webbrowser.open(url)

def main() -> None:
    """主函数，启动FastAPI应用

    从config.yaml读取服务器配置，包括host和port
    新增智能服务管理功能
    """
    # 设置日志
    logger = setup_logger()

    # 初始化服务管理器
    service_manager = get_service_manager()

    # 获取服务器配置
    host = settings.server.host
    preferred_port = settings.server.port
    reload = settings.server.reload

    # 检查服务状态
    print("=" * 70)
    print("🚀 wxautox4 RESTful API 服务管理器")
    print("=" * 70)

    service_info = service_manager.start_service(
        preferred_port=preferred_port,
        max_attempts=100,
        force_restart=False
    )

    if service_info['action'] == 'use_existing':
        # 已有运行中的服务
        port = service_info['port']
        pid = service_info['pid']
        url = f"http://127.0.0.1:{port}{settings.api.docs_url}"

        print(f"✅ {service_info['message']}")
        print(f"📡 服务地址: http://{host}:{port}")
        print(f"📚 API文档: {url}")
        print(f"🔧 进程ID: {pid}")
        print()
        print("💡 提示: 服务已在运行中，无需重复启动")
        print("💡 如需重启服务，请先停止现有进程")
        print("=" * 70)
        return

    # 启动新服务
    port = service_info['port']
    url = f"http://127.0.0.1:{port}{settings.api.docs_url}"

    print(f"🎯 {service_info['message']}")
    print("=" * 70)
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📚 API文档: {url}")
    print(f"🔄 热重载: {'启用' if reload else '禁用'}")
    print(f"🔧 进程ID: {sys.modules['os'].getpid()}")
    print("=" * 70)
    print()
    print("⏳ 正在启动服务...")
    print()

    logger.info(f"启动wxauto API服务 (端口: {port})")
    logger.info(f"服务器地址: {host}:{port}")
    logger.info(f"热重载: {'启用' if reload else '禁用'}")
    logger.info(f"API文档: {url}")

    # 通知服务已启动
    service_manager.notify_service_started(
        port=port,
        additional_info={
            "host": host,
            "reload": reload,
            "docs_url": url
        }
    )

    try:
        import threading
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

        # 启动uvicorn服务器
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=settings.logging.level.lower()
        )
    except KeyboardInterrupt:
        logger.info("服务已停止")
        service_manager.stop_service()
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        service_manager.stop_service()
        sys.exit(1)

if __name__ == "__main__":
    main() 