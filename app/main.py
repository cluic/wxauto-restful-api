from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1 import wechat, chat, apps, files, info, listen, activation
from app.utils.auth import get_current_token
from app.models.response import APIResponse
from app.utils.config import settings
from app.utils.wx_package_manager import get_supported_features
from app.middleware.concurrency import ConcurrencyControlMiddleware
from typing import Any, Dict
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI(
    title="wxautox4 API",
    description="wxautox4微信自动化API服务",
    version="2.0.0",
    docs_url=None,  # 禁用默认文档，使用自定义
    redoc_url=None,  # 禁用默认ReDoc，使用自定义
    openapi_url=settings.api.openapi_url
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.0.3"
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 挂载Web控制台（生产环境）
try:
    from fastapi.staticfiles import StaticFiles
    web_dist = Path("web/dist")
    if web_dist.exists():
        app.mount("/", StaticFiles(directory="web/dist", html=True), name="web")
except Exception:
    pass  # 开发环境可能未构建前端

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加并发控制中间件（确保微信UI操作串行执行）
app.add_middleware(ConcurrencyControlMiddleware)


# 启动事件：自动初始化微信实例
@app.on_event("startup")
async def startup_event():
    """服务启动时自动初始化微信实例"""
    from app.services.init import initialize_wechat_on_startup

    # 尝试初始化微信实例
    # 即使失败也不影响服务启动
    initialize_wechat_on_startup()

# 关闭事件：清理资源
@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时清理资源"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("正在关闭服务...")

    # 清理服务管理器状态
    try:
        from app.services.service_manager import get_service_manager
        service_manager = get_service_manager()
        service_manager.stop_service()
        logger.info("服务管理器状态已清理")
    except Exception as e:
        logger.error(f"清理服务管理器状态失败: {e}")

    # 清理微信连接（如果存在）
    try:
        from app.services.wechat_service import WeChatService
        wechat_service = WeChatService()
        if hasattr(wechat_service, 'cleanup'):
            await wechat_service.cleanup()
            logger.info("微信连接已关闭")
    except Exception as e:
        logger.error(f"关闭微信连接失败: {e}")

    # 关闭监听服务（如果正在运行）
    try:
        from app.services.listen_service import listen_service
        if hasattr(listen_service, 'stop'):
            listen_service.stop()
            logger.info("监听服务已停止")
    except Exception as e:
        logger.error(f"停止监听服务失败: {e}")

    logger.info("服务关闭完成")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一处理HTTP异常
    
    Args:
        request: 请求对象
        exc: HTTP异常
        
    Returns:
        JSONResponse: 统一格式的响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=exc.detail,
            data=None
        ).model_dump()
    )

@app.get("/")
async def root():
    """根路径

    Returns:
        dict: 欢迎信息和包信息
    """
    package_info = {
        "message": "wxauto API",
        "package": "wxautox4",
        "version": "Plus版",
        "description": "wxautox4 Plus版",
        "features_count": len(get_supported_features()),
        "docs_url": f"http://{settings.server.host}:{settings.server.port}{settings.api.docs_url}"
    }

    return package_info

# 注册路由，添加认证依赖
app.include_router(wechat.router, prefix=f"{settings.api.prefix}/wechat", tags=["WeChat"], dependencies=[Depends(get_current_token)])
# app.include_router(chat.router, prefix=f"{settings.api.prefix}/chat", tags=["Chat"], dependencies=[Depends(get_current_token)])
# app.include_router(apps.router, prefix=f"{settings.api.prefix}/apps", tags=["Apps"], dependencies=[Depends(get_current_token)])
app.include_router(files.router, prefix=f"{settings.api.prefix}/files", tags=["files"])
app.include_router(info.router, prefix=f"{settings.api.prefix}/info", tags=["Info"])
# app.include_router(listen.router, prefix=f"{settings.api.prefix}/listen", tags=["Listen"])
# 激活相关接口无需认证
app.include_router(activation.router, prefix=f"{settings.api.prefix}/activation", tags=["Activation"])

# 自定义Swagger UI路由
@app.get(settings.api.docs_url, include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI页面，使用本地静态资源"""
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
    <head>
        <title>WXAuto API - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="/static/swagger-ui/swagger-ui.css" />
        <link rel="shortcut icon" type="image/png" href="/static/swagger-ui/favicon.png">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {{
                const ui = SwaggerUIBundle({{
                    url: '/openapi.json',
                    "dom_id": "#swagger-ui",
                    "layout": "BaseLayout",
                    "deepLinking": true,
                    "showExtensions": true,
                    "showCommonExtensions": true,
                    oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                }});
            }};
        </script>
    </body>

</html>
    """)

# 自定义ReDoc路由
@app.get(settings.api.redoc_url, include_in_schema=False)
async def custom_redoc_html():
    """自定义ReDoc页面，使用本地静态资源"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WXAuto API - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body>
        <div id="redoc-container"></div>
        <script src="/static/redoc/redoc.standalone.js"></script>
        <script>
            window.onload = function() {{
                Redoc.init("{settings.api.openapi_url}", {{}}, document.getElementById("redoc-container"));
            }};
        </script>
    </body>
    </html>
    """)




