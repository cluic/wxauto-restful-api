from typing import Optional, Union, List
from app.models.response import APIResponse
from app.services.file_service import FileService
from .init import WeChat, WxClient, Chat, HumanMessage
import os

def check_wechat_alive(wx: WeChat) -> bool:
    """检查微信实例是否有效

    Args:
        wx: WeChat实例

    Returns:
        bool: 实例是否有效
    """
    try:
        # 尝试访问一个简单的属性来检查实例是否有效
        _ = wx._who
        return True
    except Exception:
        return False

def get_wechat(wxname: str) -> WeChat:
    """获取微信实例（带缓存和健康检查）

    Args:
        wxname: 微信客户端名称

    Returns:
        WeChat实例
    """
    # 如果没有指定 wxname，使用第一个缓存的实例
    if not wxname:
        if WxClient:
            # 获取第一个有效的实例
            for cached_wx in WxClient.values():
                if check_wechat_alive(cached_wx):
                    print(f"[缓存命中] 使用缓存的微信实例: {cached_wx.nickname}")
                    return cached_wx
            # 如果没有有效实例，创建新的
            print("[缓存失效] 所有缓存实例都失效，创建新实例")
            wx = WeChat()
            WxClient[wx.nickname] = wx
            print(f"[新实例] 已创建并缓存: {wx.nickname}")
            return wx
        else:
            # 缓存为空，创建新实例
            print("[缓存为空] 创建新实例")
            wx = WeChat()
            WxClient[wx.nickname] = wx
            print(f"[新实例] 已创建并缓存: {wx.nickname}")
            return wx

    # 如果指定了 wxname
    if wxname in WxClient:
        wx = WxClient[wxname]
        # 检查缓存的实例是否有效
        if check_wechat_alive(wx):
            print(f"[缓存命中] 使用缓存的微信实例: {wxname}")
            return wx
        else:
            # 实例已失效，重新创建
            print(f"[缓存失效] 微信实例 {wxname} 已失效，重新创建")
            wx = WeChat(nickname=wxname)
            WxClient[wxname] = wx
            print(f"[新实例] 已重新创建并缓存: {wxname}")
            return wx
    else:
        # 缓存中没有，创建新实例并缓存
        print(f"[缓存未命中] 实例 {wxname} 不在缓存中，创建新实例")
        wx = WeChat(nickname=wxname)
        WxClient[wxname] = wx
        print(f"[新实例] 已创建并缓存: {wxname}")
        return wx

def get_wechat_subwin(wxname: str, who: str) -> Optional[Chat]:
    """获取微信子窗口
    
    Args:
        wxname: 微信客户端名称
        who: 聊天对象
        
    Returns:
        Chat实例或None
    """
    wx = get_wechat(wxname)
    subwins = wx.GetAllSubWindow()
    if targets := [i for i in subwins if i.who == who]:
        return targets[0]
    else:
        return None

class WeChatService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeChatService, cls).__new__(cls)
        return cls._instance

    def send_message(
            self,
            msg: str,
            who: Optional[str] = None,
            clear: bool = True,
            at: Optional[str | list] = None,
            exact: bool = False,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """发送消息"""
        try:
            wx = get_wechat(wxname)
            result = wx.SendMsg(msg=msg, who=who, clear=clear, at=at, exact=exact)
            # 处理 message 可能为 None 的情况
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def send_file(
            self,
            file_id: str,
            who: Optional[str] = None,
            exact: bool = False,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """发送文件"""
        try:
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
                
        except Exception as e:
            return APIResponse(success=False, message=f"发送文件时发生错误: {str(e)}")

    def chat_with(
            self, 
            who: str,
            exact: bool = False,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """切换聊天窗口"""
        try:
            wx = get_wechat(wxname)
            result = wx.ChatWith(who=who, exact=exact)
            if result:
                return APIResponse(success=True, message='主窗口聊天切换成功', data={'chatname': result})
            else:
                return APIResponse(success=False, message='主窗口聊天切换失败')
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def get_all_sub_window(
            self,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """获取所有子窗口"""
        try:
            wx = get_wechat(wxname)
            result = wx.GetAllSubWindow()
            data = [{'name': i.who, 'type': i.chat_type} for i in result]
            return APIResponse(success=True, message='', data=data)
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def get_all_message(
            self,
            who: str,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """获取所有消息"""
        try:
            wx = get_wechat(wxname)
            if who:
                if not wx.ChatWith(who):
                    return APIResponse(success=False, message='找不到聊天窗口')
            result = wx.ChatInfo()
            msgs = wx.GetAllMessage()
            result['msg'] = [msg.info for msg in msgs]
            return APIResponse(success=True, message='', data=result)
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    # wxautox4特有功能
    def send_url_card(
            self,
            url: str,
            friends: Union[str, List[str]],
            timeout: int = 10,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """发送URL卡片"""
        try:
            wx = get_wechat(wxname)
            result = wx.SendUrlCard(url=url, friends=friends, timeout=timeout)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))
        except Exception as e:
            return APIResponse(success=False, message=str(e))
        
    def add_listen_chat(
            self,
            who: str,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """添加监听聊天"""
        
        try:
            wx = get_wechat(wxname)
            if who in [i.who for i in wx.GetAllSubWindow()]:
                return APIResponse(success=False, message='该聊天已监听中')
            wxapi = wx._api if hasattr(wx, '_api') else wx.core
            subwin = wxapi.open_separate_window(who)
            if subwin is None:
                return APIResponse(success=False, message='找不到聊天窗口')
            return APIResponse(success=True, message=f'{who} 聊天窗口已添加监听')
        except Exception as e:
            return APIResponse(success=False, message=str(e))
        
    def get_next_new_message(
            self,
            filter_mute: bool = False,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """获取下一个新消息"""
        
        try:
            wx = get_wechat(wxname)
            result = wx.GetNextNewMessage(filter_mute=filter_mute)
            if result:
                result['msg'] = [msg.info for msg in result['msg']]
            return APIResponse(success=True, message='', data=result)
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def send_quote_by_id(
            self,
            content: str,
            msg_id: str,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """根据ID发送引用消息"""
        try:
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
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def get_new_friends(
            self,
            acceptable: bool = True,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """获取新朋友"""
        try:
            wx = get_wechat(wxname)
            result = wx.GetNewFriends(acceptable=acceptable)
            return APIResponse(success=True, message='', data=result)
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def accept_new_friend(
            self,
            new_friend_id: str,
            remark: str = '',
            tags: List[str] = [],
            wxname: Optional[str] = None
        ) -> APIResponse:
        """接受新朋友"""
        try:
            wx = get_wechat(wxname)
            result = wx.AcceptNewFriend(new_friend_id=new_friend_id, remark=remark, tags=tags)
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def switch_to_chat_page(
            self,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """切换到聊天页面"""
        try:
            wx = get_wechat(wxname)
            result = wx.SwitchToChat()
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    def switch_to_contact_page(
            self,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """切换到联系人页面"""
        try:
            wx = get_wechat(wxname)
            result = wx.SwitchToContactPage()
            message = result.get('message') or '操作成功'
            return APIResponse(success=bool(result), message=message, data=result.get('data'))
        except Exception as e:
            return APIResponse(success=False, message=str(e))
        
    def is_online(
            self,
            wxname: Optional[str] = None
        ) -> APIResponse:
        """检查微信是否在线"""
        try:
            wx = get_wechat(wxname)
            result = wx.IsOnline()
            if result:
                return APIResponse(success=True, message='在线', data={'status': 'online', 'online': True})
            else:
                return APIResponse(success=True, message='离线', data={'status': 'offline', 'online': False})
        except Exception as e:
            return APIResponse(success=False, message=str(e))