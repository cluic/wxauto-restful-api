from app.utils.wx_package_manager import wx_manager, get_wx_class, get_wx_function
from pythoncom import CoInitialize


# 动态导入wx包
WeChat = get_wx_class("WeChat")
Chat = get_wx_class("Chat")
HumanMessage = wx_manager.package.msgs.base.HumanMessage
try:
    get_wx_clients = get_wx_function("get_wx_clients")
except:
    def get_wx_clients():
        return [WeChat()]

# 初始化COM
CoInitialize()

# 导入 wxautox4 额外模块
try:
    WxResponse = wx_manager.package.param.WxResponse
except Exception as e:
    print(f"警告：无法导入WxResponse: {e}")

# 获取微信客户端（全局缓存字典）
WxClient = {}
try:
    clients = get_wx_clients()
    for client in clients:
        WxClient[client.nickname] = client
        # 尝试停止监听，如果失败也不影响缓存
        try:
            client.StopListening()
        except Exception:
            pass  # 忽略 StopListening 错误
    print(f"成功初始化 {len(WxClient)} 个微信客户端实例")
except Exception as e:
    print(f"警告：获取微信客户端时出错: {e}")