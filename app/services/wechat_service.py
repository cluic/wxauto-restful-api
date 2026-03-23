"""WeChat Service with Queue-Based Operations"""
import asyncio
import os
from typing import Optional, Union, List
from app.models.response import APIResponse
from app.services.file_service import FileService
from app.services.operation_queue import OperationQueue
from app.services.executor import UIOperationExecutor
from app.utils.error_handler import handle_service_error
from .init import WeChat, WxClient, Chat, HumanMessage, safe_initialize_wechat
import time


class WeChatNotInitializedError(Exception):
    """微信实例未初始化异常"""
    pass


def check_wechat_alive(wx: WeChat) -> bool:
    """检查微信实例是否有效

    Args:
        wx: WeChat实例

    Returns:
        bool: 实例是否有效
    """
    try:
        return wx.IsOnline()
    except Exception:
        return False


def get_wechat(wxname: str) -> WeChat:
    """获取微信实例（带缓存和健康检查）

    Args:
        wxname: 微信客户端名称

    Returns:
        WeChat实例

    Raises:
        WeChatNotInitializedError: 如果微信未激活或初始化失败
    """
    # 首先尝试初始化（如果还没初始化）
    if not safe_initialize_wechat():
        # 初始化失败，抛出异常
        raise WeChatNotInitializedError(
            "微信实例未就绪。请先调用 /api/v1/wechat/initialize 接口获取实例。"
            "确保微信已登录，如提示未激活请运行: wxautox4 -a your-activation-code"
        )

    # 如果没有指定 wxname，使用第一个缓存的实例
    if not wxname:
        if WxClient:
            # 获取第一个有效的实例
            for cached_wx in WxClient.values():
                if check_wechat_alive(cached_wx):
                    print(f"[缓存命中] 使用缓存的微信实例: {cached_wx.nickname}", flush=True)
                    return cached_wx
            # 如果没有有效实例，尝试创建新的
            print("[缓存失效] 所有缓存实例都失效，尝试创建新实例", flush=True)
            try:
                wx = WeChat()
                WxClient[wx.nickname] = wx
                print(f"[新实例] 已创建并缓存: {wx.nickname}", flush=True)
                return wx
            except Exception as e:
                error_msg = f"无法创建微信实例: {e}"
                print(f"[创建失败] {error_msg}", flush=True)
                raise WeChatNotInitializedError(
                    f"微信实例已失效且无法重新创建。请调用 /api/v1/wechat/initialize 重新初始化。错误信息: {error_msg}"
                )
        else:
            # 缓存为空，尝试创建新实例
            print("[缓存为空] 尝试创建新实例", flush=True)
            try:
                wx = WeChat()
                WxClient[wx.nickname] = wx
                print(f"[新实例] 已创建并缓存: {wx.nickname}", flush=True)
                return wx
            except Exception as e:
                error_msg = f"无法创建微信实例: {e}"
                print(f"[创建失败] {error_msg}", flush=True)
                raise WeChatNotInitializedError(
                    f"无法获取微信实例。请先调用 /api/v1/wechat/initialize 接口。错误信息: {error_msg}"
                )

    # 如果指定了 wxname
    if wxname in WxClient:
        wx = WxClient[wxname]
        # 检查缓存的实例是否有效
        if check_wechat_alive(wx):
            print(f"[缓存命中] 使用缓存的微信实例: {wxname}", flush=True)
            return wx
        else:
            # 实例已失效，尝试重新创建
            print(f"[缓存失效] 微信实例 {wxname} 已失效，尝试重新创建", flush=True)
            try:
                wx = WeChat(nickname=wxname)
                WxClient[wxname] = wx
                print(f"[新实例] 已重新创建并缓存: {wxname}", flush=True)
                return wx
            except Exception as e:
                error_msg = f"无法重新创建微信实例: {e}"
                print(f"[创建失败] {error_msg}", flush=True)
                raise WeChatNotInitializedError(
                    f"微信实例已失效。请调用 /api/v1/wechat/initialize 重新初始化。错误信息: {error_msg}"
                )
    else:
        # 缓存中没有，创建新实例并缓存
        print(f"[缓存未命中] 实例 {wxname} 不在缓存中，创建新实例", flush=True)
        try:
            wx = WeChat(nickname=wxname)
            WxClient[wxname] = wx
            print(f"[新实例] 已创建并缓存: {wxname}", flush=True)
            return wx
        except Exception as e:
            error_msg = f"无法创建微信实例: {e}"
            print(f"[创建失败] {error_msg}", flush=True)
            raise WeChatNotInitializedError(
                f"无法获取微信实例。请调用 /api/v1/wechat/initialize 接口。错误信息: {error_msg}"
            )


def get_wechat_subwin(wxname: str, who: str) -> Optional[Chat]:
    """获取微信子窗口

    Args:
        wxname: 微信客户端名称
        who: 聊天对象

    Returns:
        Chat实例或None
    """
    try:
        wx = get_wechat(wxname)
    except WeChatNotInitializedError:
        return None

    try:
        subwins = wx.GetAllSubWindow()
        if targets := [i for i in subwins if i.who == who]:
            return targets[0]
        else:
            return None
    except Exception:
        return None


def get_raw_messages(msgs, chat_info):
    # result = {}
    raw_msgs = []
    if msgs:
        
        for msg in msgs:
            raw = msg.raw.copy()
            items = list(raw.keys())
            for item in items:
                if item in chat_info:
                    raw.pop(item)
            raw_msgs.append(raw)
    # result['chat_info'] = chat_info
    # result['msg'] = raw_msgs
    return raw_msgs

def safe_switch_chat(wx, target: str, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            wx.ChatWith(who=target)
            time.sleep(0.5)
            if wx.ChatInfo().get('chat_name') == target:
                return True
        except Exception as e:
            print(f"发送失败 ({attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    return False

def safe_send_msg(wx, target: str, msg: str, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            wx.ChatWith(who=target)
            time.sleep(0.5)
            if wx.ChatInfo().get('chat_name') == target:
                result = wx.SendMsg(msg=msg)
                return True
        except Exception as e:
            print(f"发送失败 ({attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    return False


class WeChatService:
    """WeChat服务类，使用队列执行所有操作以保证线程安全"""

    _instance = None
    _queue: Optional[OperationQueue] = None
    _executor: Optional[UIOperationExecutor] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeChatService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化队列和执行器"""
        if not self._initialized:
            self._queue = OperationQueue(max_concurrent=1)
            self._executor = UIOperationExecutor()
            self._executor.start()
            self._initialized = True
            print("[WeChatService] 服务已初始化，队列执行器已启动", flush=True)

    async def send_message(
            self,
            msg: str,
            who: Optional[str] = None,
            clear: bool = True,
            at: Optional[str | list] = None,
            exact: bool = False,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """发送消息"""
        @handle_service_error(custom_message="发送消息失败")
        def _send():
            wx = get_wechat(wxname)
            if wx is None:
                return APIResponse(
                    success=False,
                    message="wxautox4未激活，无法使用微信功能",
                    data={
                        "error": "NOT_ACTIVATED",
                        "solution": "请先运行: wxautox4 -a your-activation-code"
                    }
                )

            # result = wx.SendMsg(msg=msg, who=who, clear=clear, at=at, exact=exact)
            result = safe_send_msg(wx, target=who, msg=msg)
            if result:
                return APIResponse(success=True, message='发送成功')
            else:
                return APIResponse(success=False, message='发送失败')
        return await self._queue.submit(_send)

    @handle_service_error(custom_message="发送消息失败")
    def send_message_sync(
            self,
            msg: str,
            who: Optional[str] = None,
            clear: bool = True,
            at: Optional[str | list] = None,
            exact: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送消息（同步接口）"""
        wx = get_wechat(wxname)
        # result = wx.SendMsg(msg=msg, who=who, clear=clear, at=at, exact=exact)
        result = safe_send_msg(wx, target=who, msg=msg)
        if result:
            return APIResponse(success=True, message='发送成功')
        else:
            return APIResponse(success=False, message='发送失败')

    async def send_file(
            self,
            file_id: str,
            who: Optional[str] = None,
            exact: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送文件"""
        @handle_service_error(custom_message="发送文件失败")
        def _send_file():
            # 获取文件信息
            file_service = FileService()
            file_info = file_service.get_file(file_id)
            if not file_info:
                return APIResponse(success=False, message="文件不存在")

            # 检查文件是否存在
            if not file_info.file_path or not os.path.exists(file_info.file_path):
                return APIResponse(success=False, message="文件路径不存在")

            # 发送文件
            wx = get_wechat(wxname)
            result = wx.SendFiles(filepath=file_info.file_path, who=who, exact=exact)

            if result:
                return APIResponse(
                    success=True,
                    message="文件发送成功",
                    data={
                        "file_id": file_id,
                        "filename": file_info.filename,
                        "file_path": file_info.file_path,
                        "recipient": who
                    }
                )
            else:
                return APIResponse(success=False, message="文件发送失败")

        return await self._queue.submit(_send_file)

    @handle_service_error(custom_message="发送文件失败")
    def send_file_sync(
            self,
            file_id: str,
            who: Optional[str] = None,
            exact: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送文件（同步接口）"""
        # 获取文件信息
        file_service = FileService()
        file_info = file_service.get_file(file_id)
        if not file_info:
            return APIResponse(success=False, message="文件不存在")

        # 检查文件是否存在
        if not file_info.file_path or not os.path.exists(file_info.file_path):
            return APIResponse(success=False, message="文件路径不存在")

        # 发送文件
        wx = get_wechat(wxname)
        if not safe_switch_chat(wx, target=who):
            return APIResponse(success=False, message="文件发送失败")
        result = wx.SendFiles(filepath=file_info.file_path)

        if result:
            return APIResponse(
                success=True,
                message="文件发送成功",
                data={
                    "file_id": file_id,
                    "filename": file_info.filename,
                    "file_path": file_info.file_path,
                    "recipient": who
                }
            )
        else:
            return APIResponse(success=False, message="文件发送失败")

    async def chat_with(
            self,
            who: str,
            exact: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换聊天窗口"""
        @handle_service_error(custom_message="切换聊天窗口失败")
        def _chat_with():
            from app.utils.response_builder import single_object, error

            wx = get_wechat(wxname)
            result = safe_switch_chat(wx, target=who)
            if result:
                chat_info = wx.ChatInfo()
                return single_object(
                    obj={"name": chat_info.get('chat_name'), "type": chat_info.get('chat_type')},
                    message='主窗口聊天切换成功'
                )
            else:
                return error(message='主窗口聊天切换失败', error_code='SWITCH_FAILED')

        return await self._queue.submit(_chat_with)

    @handle_service_error(custom_message="切换聊天窗口失败")
    def chat_with_sync(
            self,
            who: str,
            exact: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换聊天窗口（同步接口）"""
        from app.utils.response_builder import single_object, error

        wx = get_wechat(wxname)
        result = safe_switch_chat(wx, target=who)
        if result:
            chat_info = wx.ChatInfo()
            return single_object(
                obj={"name": chat_info.get('chat_name'), "type": chat_info.get('chat_type')},
                message='主窗口聊天切换成功'
            )
        else:
            return error(message='主窗口聊天切换失败', error_code='SWITCH_FAILED')

    async def get_all_sub_window(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取所有子窗口"""
        @handle_service_error(custom_message="获取子窗口失败")
        def _get_all():
            from app.utils.response_builder import list_response

            wx = get_wechat(wxname)
            result = wx.GetAllSubWindow()
            items = [{'id': i.who, 'name': i.who, 'type': i.chat_type} for i in result]
            return list_response(items=items, message="")

        return await self._queue.submit(_get_all)

    @handle_service_error(custom_message="获取子窗口失败")
    def get_all_sub_window_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取所有子窗口（同步接口）"""
        from app.utils.response_builder import list_response

        wx = get_wechat(wxname)
        result = wx.GetAllSubWindow()
        items = [{'id': i.who, 'name': i.who, 'type': i.chat_type} for i in result]
        return list_response(items=items, message="")

    async def get_all_message(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取所有消息"""
        @handle_service_error(custom_message="获取消息失败")
        def _get_all():
            from app.utils.response_builder import message_data, error

            wx = get_wechat(wxname)
            if who:
                if not safe_switch_chat(wx, target=who):
                    return error(message='找不到聊天窗口', error_code='CHAT_NOT_FOUND')
            msgs = wx.GetAllMessage()
            chat_info = wx.ChatInfo()
            # raw_msgs = get_raw_messages(msgs, chat_info)
            raw_msgs = get_raw_messages(msgs, chat_info)
            return message_data(messages=raw_msgs, chat_info=chat_info, message="")

        return await self._queue.submit(_get_all)

    @handle_service_error(custom_message="获取消息失败")
    def get_all_message_sync(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取所有消息（同步接口）"""
        from app.utils.response_builder import message_data, error

        wx = get_wechat(wxname)
        if who:
            if not safe_switch_chat(wx, target=who):
                return error(message='找不到聊天窗口', error_code='CHAT_NOT_FOUND')
        chat_info = wx.ChatInfo()
        msgs = wx.GetAllMessage()
        raw_msgs = [msg.info for msg in msgs]
        return message_data(messages=raw_msgs, chat_info=chat_info, message="")

    # wxautox4特有功能
    async def send_url_card(
            self,
            url: str,
            friends: Union[str, List[str]],
            timeout: int = 10,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送URL卡片"""
        @handle_service_error(custom_message="发送URL卡片失败")
        def _send_card():
            wx = get_wechat(wxname)
            result = wx.SendUrlCard(url=url, friends=friends, timeout=timeout)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))

        return await self._queue.submit(_send_card)

    @handle_service_error(custom_message="发送URL卡片失败")
    def send_url_card_sync(
            self,
            url: str,
            friends: Union[str, List[str]],
            timeout: int = 10,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送URL卡片（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.SendUrlCard(url=url, friends=friends, timeout=timeout)
        message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message=message, data=result.get('data'))

    async def add_listen_chat(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """添加监听聊天"""
        @handle_service_error(custom_message="添加监听失败")
        def _add_listen():
            wx = get_wechat(wxname)
            if who in [i.who for i in wx.GetAllSubWindow()]:
                return APIResponse(success=False, message='该聊天已监听中')
            wxapi = wx._api if hasattr(wx, '_api') else wx.core
            subwin = wxapi.open_separate_window(who)
            if subwin is None:
                return APIResponse(success=False, message='找不到聊天窗口')
            return APIResponse(success=True, message=f'{who} 聊天窗口已添加监听')

        return await self._queue.submit(_add_listen)

    @handle_service_error(custom_message="添加监听失败")
    def add_listen_chat_sync(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """添加监听聊天（同步接口）"""
        wx = get_wechat(wxname)
        if who in [i.who for i in wx.GetAllSubWindow()]:
            return APIResponse(success=False, message='该聊天已监听中')
        wxapi = wx._api if hasattr(wx, '_api') else wx.core
        subwin = wxapi.open_separate_window(who)
        if subwin is None:
            return APIResponse(success=False, message='找不到聊天窗口')
        return APIResponse(success=True, message=f'{who} 聊天窗口已添加监听')

    async def get_next_new_message(
            self,
            filter_mute: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取下一个新消息"""
        @handle_service_error(custom_message="获取新消息失败")
        def _get_next():
            from app.utils.response_builder import message_data

            wx = get_wechat(wxname)
            next_msgs = wx.GetNextNewMessage(filter_mute=filter_mute)
            chat_info = wx.ChatInfo()
            msgs = next_msgs.get('msg', [])
            raw_msgs = get_raw_messages(msgs, chat_info)
            return message_data(messages=raw_msgs, chat_info=chat_info, message="")

        return await self._queue.submit(_get_next)

    @handle_service_error(custom_message="获取新消息失败")
    def get_next_new_message_sync(
            self,
            filter_mute: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取下一个新消息（同步接口）"""
        from app.utils.response_builder import message_data

        wx = get_wechat(wxname)
        next_msgs = wx.GetNextNewMessage(filter_mute=filter_mute)
        chat_info = wx.ChatInfo()
        msgs = next_msgs.get('msg', [])
        raw_msgs = get_raw_messages(msgs, chat_info)
        return message_data(messages=raw_msgs, chat_info=chat_info, message="")

    async def send_quote_by_id(
            self,
            content: str,
            msg_id: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """根据ID发送引用消息"""
        @handle_service_error(custom_message="发送引用消息失败")
        def _send_quote():
            wx = get_wechat(wxname)
            if (msg := wx.GetMessageById(msg_id)) is not None:
                if isinstance(msg, HumanMessage):
                    result = msg.quote(text=content)
                    message = result.get('message') or '操作成功'
                    return APIResponse(success=bool(result), message=message, data=result.get('data'))
                else:
                    return APIResponse(success=False, message=f'当前消息不可引用(消息类型："{msg.type}"  内容："{msg.content}")')
            else:
                return APIResponse(success=False, message=f"消息不存在：{msg_id}")

        return await self._queue.submit(_send_quote)

    @handle_service_error(custom_message="发送引用消息失败")
    def send_quote_by_id_sync(
            self,
            content: str,
            msg_id: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """根据ID发送引用消息（同步接口）"""
        wx = get_wechat(wxname)
        if (msg := wx.GetMessageById(msg_id)) is not None:
            if isinstance(msg, HumanMessage):
                result = msg.quote(text=content)
                message = result.get('message') or '操作成功'
                return APIResponse(success=bool(result), message=message, data=result.get('data'))
            else:
                return APIResponse(success=False, message=f'当前消息不可引用(消息类型："{msg.type}"  内容："{msg.content}")')
        else:
            return APIResponse(success=False, message=f"消息不存在：{msg_id}")

    async def get_new_friends(
            self,
            acceptable: bool = True,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取新朋友"""
        @handle_service_error(custom_message="获取新朋友失败")
        def _get_friends():
            wx = get_wechat(wxname)
            result = wx.GetNewFriends(acceptable=acceptable)
            return APIResponse(success=True, message='', data=result)

        return await self._queue.submit(_get_friends)

    @handle_service_error(custom_message="获取新朋友失败")
    def get_new_friends_sync(
            self,
            acceptable: bool = True,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取新朋友（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.GetNewFriends(acceptable=acceptable)
        return APIResponse(success=True, message='', data=result)

    async def accept_new_friend(
            self,
            new_friend_id: str,
            remark: str = '',
            tags: List[str] = [],
            wxname: Optional[str] = None
    ) -> APIResponse:
        """接受新朋友"""
        @handle_service_error(custom_message="接受新朋友失败")
        def _accept_friend():
            wx = get_wechat(wxname)
            result = wx.AcceptNewFriend(new_friend_id=new_friend_id, remark=remark, tags=tags)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))

        return await self._queue.submit(_accept_friend)

    @handle_service_error(custom_message="接受新朋友失败")
    def accept_new_friend_sync(
            self,
            new_friend_id: str,
            remark: str = '',
            tags: List[str] = [],
            wxname: Optional[str] = None
    ) -> APIResponse:
        """接受新朋友（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.AcceptNewFriend(new_friend_id=new_friend_id, remark=remark, tags=tags)
        message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message=message, data=result.get('data'))

    async def switch_to_chat_page(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换到聊天页面"""
        @handle_service_error(custom_message="切换到聊天页面失败")
        def _switch_chat():
            wx = get_wechat(wxname)
            result = wx.SwitchToChat()
            # message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message='操作成功', data=None)

        return await self._queue.submit(_switch_chat)

    @handle_service_error(custom_message="切换到聊天页面失败")
    def switch_to_chat_page_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换到聊天页面（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.SwitchToChat()
        # message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message='操作成功', data=None)

    async def switch_to_contact_page(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换到联系人页面"""
        @handle_service_error(custom_message="切换到联系人页面失败")
        def _switch_contact():
            wx = get_wechat(wxname)
            result = wx.SwitchToContact()
            # message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message='操作成功', data=None)

        return await self._queue.submit(_switch_contact)

    @handle_service_error(custom_message="切换到联系人页面失败")
    def switch_to_contact_page_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """切换到联系人页面（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.SwitchToContact()
        # message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message='操作成功', data=None)

    async def is_online(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """检查微信是否在线"""
        @handle_service_error(custom_message="检查在线状态失败")
        def _check_online():
            from app.utils.response_builder import single_object

            wx = get_wechat(wxname)
            result = wx.IsOnline()
            status_data = {
                "status": "online" if result else "offline",
                "online": result
            }
            return single_object(
                obj=status_data,
                message='在线' if result else '离线'
            )

        return await self._queue.submit(_check_online)

    @handle_service_error(custom_message="检查在线状态失败")
    def is_online_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """检查微信是否在线（同步接口）"""
        from app.utils.response_builder import single_object

        wx = get_wechat(wxname)
        result = wx.IsOnline()
        status_data = {
            "status": "online" if result else "offline",
            "online": result
        }
        return single_object(
            obj=status_data,
            message='在线' if result else '离线'
        )

    # 新增：获取会话列表
    async def get_session(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取当前会话列表"""
        @handle_service_error(custom_message="获取会话列表失败")
        def _get_session():
            from app.utils.response_builder import list_response, wechat_not_ready

            wx = get_wechat(wxname)
            if wx is None:
                return wechat_not_ready()

            result = wx.GetSession()
            items = [session.info for session in result]
            return list_response(items=items, message="")

        return await self._queue.submit(_get_session)

    @handle_service_error(custom_message="获取会话列表失败")
    def get_session_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取当前会话列表（同步接口）"""
        from app.utils.response_builder import list_response, wechat_not_ready

        wx = get_wechat(wxname)
        if wx is None:
            return wechat_not_ready()

        result = wx.GetSession()
        items = [session.info for session in result]
        return list_response(items=items, message="")

    # 新增：获取子窗口
    async def get_sub_window(
            self,
            nickname: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取指定子窗口"""
        @handle_service_error(custom_message="获取子窗口失败")
        def _get_sub_window():
            from app.utils.response_builder import single_object, error

            wx = get_wechat(wxname)
            result = wx.GetSubWindow(nickname=nickname)
            if result:
                return single_object(
                    obj={"name": result.who, "type": result.chat_type},
                    message=""
                )
            else:
                return error(message='找不到该聊天窗口', error_code='SUBWINDOW_NOT_FOUND')

        return await self._queue.submit(_get_sub_window)

    @handle_service_error(custom_message="获取子窗口失败")
    def get_sub_window_sync(
            self,
            nickname: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取指定子窗口（同步接口）"""
        from app.utils.response_builder import single_object, error

        wx = get_wechat(wxname)
        result = wx.GetSubWindow(nickname=nickname)
        if result:
            return single_object(
                obj={"name": result.who, "type": result.chat_type},
                message=""
            )
        else:
            return error(message='找不到该聊天窗口', error_code='SUBWINDOW_NOT_FOUND')

    # 新增：移除监听
    async def remove_listen_chat(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """移除监听聊天"""
        @handle_service_error(custom_message="移除监听失败")
        def _remove_listen():
            wx = get_wechat(wxname)
            result = wx.RemoveListenChat(nickname=who)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))

        return await self._queue.submit(_remove_listen)

    @handle_service_error(custom_message="移除监听失败")
    def remove_listen_chat_sync(
            self,
            who: str,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """移除监听聊天（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.RemoveListenChat(nickname=who)
        message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message=message, data=result.get('data'))

    # 新增：获取历史消息
    async def get_history_message(
            self,
            who: str,
            n: int = 50,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取历史消息"""
        @handle_service_error(custom_message="获取历史消息失败")
        def _get_history():
            from app.utils.response_builder import message_data, error

            wx = get_wechat(wxname)
            # 先切换到指定聊天窗口
            if not safe_switch_chat(wx, target=who):
                return error(message='找不到聊天窗口', error_code='CHAT_NOT_FOUND')
            # 获取历史消息
            msgs = wx.GetHistoryMessage(n=n)
            chat_info = wx.ChatInfo()
            raw_msgs = get_raw_messages(msgs, chat_info)
            return message_data(messages=raw_msgs, chat_info=chat_info, message="")

        return await self._queue.submit(_get_history)

    @handle_service_error(custom_message="获取历史消息失败")
    def get_history_message_sync(
            self,
            who: str,
            n: int = 50,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取历史消息（同步接口）"""
        from app.utils.response_builder import message_data, error

        wx = get_wechat(wxname)
        # 先切换到指定聊天窗口
        if not safe_switch_chat(wx, target=who):
            return error(message='找不到聊天窗口', error_code='CHAT_NOT_FOUND')
        # 获取历史消息
        msgs = wx.GetHistoryMessage(n=n)
        chat_info = wx.ChatInfo()
        raw_msgs = get_raw_messages(msgs, chat_info)
        return message_data(messages=raw_msgs, chat_info=chat_info, message="")

    # 新增：获取群聊列表
    async def get_all_recent_groups(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取最近群聊列表"""
        @handle_service_error(custom_message="获取群聊列表失败")
        def _get_groups():
            from app.utils.response_builder import list_response, error

            wx = get_wechat(wxname)
            result = wx.GetAllRecentGroups()
            # 判断返回类型
            if hasattr(result, '__iter__') and not isinstance(result, dict):
                # 成功返回列表
                items = list(result)
                return list_response(items=items, message="")
            else:
                # 失败返回WxResponse
                message = result.get('message') if hasattr(result, 'get') else '获取失败'
                return error(message=message)

        return await self._queue.submit(_get_groups)

    @handle_service_error(custom_message="获取群聊列表失败")
    def get_all_recent_groups_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取最近群聊列表（同步接口）"""
        from app.utils.response_builder import list_response, error

        wx = get_wechat(wxname)
        result = wx.GetAllRecentGroups()
        # 判断返回类型
        if hasattr(result, '__iter__') and not isinstance(result, dict):
            # 成功返回列表
            items = list(result)
            return list_response(items=items, message="")
        else:
            # 失败返回WxResponse
            message = result.get('message') if hasattr(result, 'get') else '获取失败'
            return error(message=message)

    # 新增：获取好友列表
    async def get_friend_details(
            self,
            n: Optional[int] = None,
            save_head_image: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取好友详情列表"""
        @handle_service_error(custom_message="获取好友列表失败")
        def _get_friends():
            from app.utils.response_builder import list_response

            wx = get_wechat(wxname)
            result = wx.GetFriendDetails(n=n, save_head_image=save_head_image)
            wx.SwitchToChat()
            return list_response(items=result, message="")

        return await self._queue.submit(_get_friends)

    @handle_service_error(custom_message="获取好友列表失败")
    def get_friend_details_sync(
            self,
            n: Optional[int] = None,
            save_head_image: bool = False,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取好友详情列表（同步接口）"""
        from app.utils.response_builder import list_response

        wx = get_wechat(wxname)
        result = wx.GetFriendDetails(n=n, save_head_image=save_head_image)
        return list_response(items=result, message="")

    # 新增：获取我的信息
    async def get_my_info(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取我的账号信息"""
        @handle_service_error(custom_message="获取账号信息失败")
        def _get_info():
            from app.utils.response_builder import single_object

            wx = get_wechat(wxname)
            result = wx.GetMyInfo()
            return single_object(obj=result, message="")

        return await self._queue.submit(_get_info)

    @handle_service_error(custom_message="获取账号信息失败")
    def get_my_info_sync(
            self,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """获取我的账号信息（同步接口）"""
        from app.utils.response_builder import single_object

        wx = get_wechat(wxname)
        result = wx.GetMyInfo()
        return single_object(obj=result, message="")

    # 新增：添加好友
    async def add_new_friend(
            self,
            keywords: str,
            addmsg: Optional[str] = None,
            remark: Optional[str] = None,
            tags: Optional[List[str]] = None,
            permission: str = '朋友圈',
            timeout: int = 5,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """添加新的好友"""
        @handle_service_error(custom_message="添加好友失败")
        def _add_friend():
            wx = get_wechat(wxname)
            result = wx.AddNewFriend(
                keywords=keywords,
                addmsg=addmsg,
                remark=remark,
                tags=tags,
                permission=permission,
                timeout=timeout
            )
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))

        return await self._queue.submit(_add_friend)

    @handle_service_error(custom_message="添加好友失败")
    def add_new_friend_sync(
            self,
            keywords: str,
            addmsg: Optional[str] = None,
            remark: Optional[str] = None,
            tags: Optional[List[str]] = None,
            permission: str = '朋友圈',
            timeout: int = 5,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """添加新的好友（同步接口）"""
        wx = get_wechat(wxname)
        result = wx.AddNewFriend(
            keywords=keywords,
            addmsg=addmsg,
            remark=remark,
            tags=tags,
            permission=permission,
            timeout=timeout
        )
        message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message=message, data=result.get('data'))

    # 新增：进入朋友圈
    async def moments(
            self,
            timeout: int = 3,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """进入朋友圈"""
        @handle_service_error(custom_message="进入朋友圈失败")
        def _moments():
            from app.utils.response_builder import single_object, error

            wx = get_wechat(wxname)
            result = wx.Moments(timeout=timeout)
            if result:
                return single_object(
                    obj={"status": "entered"},
                    message='已进入朋友圈'
                )
            else:
                return error(message='进入朋友圈失败', error_code='MOMENTS_FAILED')

        return await self._queue.submit(_moments)

    @handle_service_error(custom_message="进入朋友圈失败")
    def moments_sync(
            self,
            timeout: int = 3,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """进入朋友圈（同步接口）"""
        from app.utils.response_builder import single_object, error

        wx = get_wechat(wxname)
        result = wx.Moments(timeout=timeout)
        if result:
            return single_object(
                obj={"status": "entered"},
                message='已进入朋友圈'
            )
        else:
            return error(message='进入朋友圈失败', error_code='MOMENTS_FAILED')

    # 新增：发送朋友圈
    async def publish_moment(
            self,
            text: str,
            media_files: Optional[List[str]] = None,
            privacy: Optional[dict] = None,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送朋友圈"""
        @handle_service_error(custom_message="发送朋友圈失败")
        def _publish():
            wx = get_wechat(wxname)
            # 如果没有提供隐私配置，使用默认的公开发布
            privacy_config = privacy if privacy else {}
            # 检查媒体文件是否存在
            if media_files:
                for file_path in media_files:
                    if not os.path.exists(file_path):
                        return APIResponse(success=False, message=f'文件不存在: {file_path}')
            result = wx.PublishMoment(text=text, media_files=media_files, privacy_config=privacy_config)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))

        return await self._queue.submit(_publish)

    @handle_service_error(custom_message="发送朋友圈失败")
    def publish_moment_sync(
            self,
            text: str,
            media_files: Optional[List[str]] = None,
            privacy: Optional[dict] = None,
            wxname: Optional[str] = None
    ) -> APIResponse:
        """发送朋友圈（同步接口）"""
        wx = get_wechat(wxname)
        # 如果没有提供隐私配置，使用默认的公开发布
        privacy_config = privacy if privacy else {}
        # 检查媒体文件是否存在
        if media_files:
            for file_path in media_files:
                if not os.path.exists(file_path):
                    return APIResponse(success=False, message=f'文件不存在: {file_path}')
        result = wx.PublishMoment(text=text, media_files=media_files, privacy_config=privacy_config)
        message = result.get('message') or '操作成功'
        return APIResponse(success=bool(result), message=message, data=result.get('data'))

    async def close(self):
        """关闭服务并清理资源"""
        if self._queue:
            await self._queue.close()
        if self._executor:
            self._executor.stop()
        self._initialized = False
        print("[WeChatService] 服务已关闭", flush=True)

    def __del__(self):
        """清理资源"""
        try:
            if self._executor and self._executor.is_running():
                self._executor.stop()
        except:
            pass