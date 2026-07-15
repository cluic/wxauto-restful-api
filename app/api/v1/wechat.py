from fastapi import APIRouter, Request, Depends
from app.services.wechat_service import WeChatService
from app.models.request.wechat import *
from app.models.response import APIResponse
from typing import Dict, Any
import asyncio

router = APIRouter()


@router.post(
    "/initialize",
    operation_id="[wx]获取微信实例",
    response_model=APIResponse,
    summary="🔑 获取/初始化微信实例（核心功能前置接口）"
)
async def initialize_wechat():
    """获取或初始化微信实例

    此接口用于：
    1. 检测微信是否已激活
    2. 获取微信实例并全局缓存
    3. 供后续核心功能使用

    建议：
    - 服务启动时会自动调用此接口
    - 如果初始化失败，可手动调用此接口重试
    - 使用其他核心功能前建议先调用此接口

    Returns:
        APIResponse: 包含初始化状态和微信实例信息
    """
    from app.services.init import initialize_wechat_on_startup, get_initialization_status

    # 检查当前状态
    status = get_initialization_status()

    if status['clients_count'] > 0:
        return APIResponse(
            success=True,
            message=f"微信实例已就绪，当前有 {status['clients_count']} 个客户端",
            data={
                "status": "ready",
                "clients_count": status['clients_count'],
                "clients": status['clients']
            }
        )

    # 尝试初始化
    result = initialize_wechat_on_startup()

    if result['success']:
        return APIResponse(
            success=True,
            message=result['message'],
            data={
                "status": "initialized",
                "clients_count": result['clients_count'],
                "clients": result['clients']
            }
        )
    else:
        return APIResponse(
            success=False,
            message=result['message'],
            data={
                "status": "failed",
                "error": "INITIALIZATION_FAILED",
                "solution": "请确保微信已登录，或先激活 wxautox4"
            }
        )


@router.get(
    "/status",
    operation_id="[wx]获取实例状态",
    response_model=APIResponse,
    summary="查看微信实例状态"
)
async def get_wechat_status():
    """获取微信实例当前状态

    Returns:
        APIResponse: 包含初始化状态和客户端信息
    """
    from app.services.init import get_initialization_status

    status = get_initialization_status()

    if status['clients_count'] > 0:
        return APIResponse(
            success=True,
            message=f"微信实例运行中，当前有 {status['clients_count']} 个客户端",
            data={
                "status": "running",
                "clients_count": status['clients_count'],
                "clients": status['clients'],
                "initialized": status['initialized'],
                "attempted": status['attempted']
            }
        )
    else:
        return APIResponse(
            success=False,
            message="微信实例未就绪",
            data={
                "status": "not_ready",
                "clients_count": 0,
                "clients": [],
                "initialized": status['initialized'],
                "attempted": status['attempted'],
                "solution": "请调用 /api/v1/wechat/initialize 接口初始化"
            }
        )

@router.post(
    "/send", 
    operation_id="[wx]发送消息", 
    response_model=APIResponse,
    summary="发送文字消息"
)
async def send_message(
    request: SendMessageRequest,
    service: WeChatService = Depends()
):
    """微信主窗口发送消息"""
    return await service.send_message(
        msg=request.msg,
        who=request.who,
        clear=request.clear,
        at=request.at,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/sendfile", 
    operation_id="[wx]发送文件", 
    response_model=APIResponse,
    summary="发送文件、图片、视频等（请先调用上传文件接口）"
)
async def send_file(
    request: SendFileRequest,
    service: WeChatService = Depends()
):
    """微信主窗口发送文件"""
    return await service.send_file(
        file_id=request.file_id,
        who=request.who,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/chatwith",
    operation_id="[wx]切换聊天窗口",
    response_model=APIResponse,
    summary="切换聊天窗口"
)
async def chat_with(
    request: ChatWithRequest,
    service: WeChatService = Depends()
):
    """微信主窗口切换聊天窗口"""
    result = await service.chat_with(
        who=request.who,
        exact=request.exact,
        wxname=request.wxname
    )
    return result

@router.post(
    "/chatinfo",
    operation_id="[wx]获取聊天信息",
    response_model=APIResponse,
    summary="获取当前或指定聊天窗口信息"
)
async def get_chat_info(
    request: ChatInfoRequest,
    service: WeChatService = Depends()
):
    """获取聊天信息；指定 who 时先切换到该聊天。"""
    return await service.get_chat_info(
        who=request.who,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/getsession",
    operation_id="[wx]获取会话列表",
    response_model=APIResponse,
    summary="获取当前会话列表"
)
async def get_session(
    request: GetSessionRequest,
    service: WeChatService = Depends()
):
    """获取当前会话列表"""
    return await service.get_session(wxname=request.wxname)

@router.post(
    "/getallsubwindow",
    operation_id="[wx]获取所有子窗口",
    response_model=APIResponse,
    summary="获取所有子窗口信息"
)
async def get_all_sub_window(
    request: GetAllSubWindowRequest,
    service: WeChatService = Depends()
):
    """获取微信所有子窗口信息"""
    return await service.get_all_sub_window(wxname=request.wxname)

@router.post(
    "/getsubwindow",
    operation_id="[wx]获取指定子窗口",
    response_model=APIResponse,
    summary="获取指定聊天窗口信息"
)
async def get_sub_window(
    request: GetSubWindowRequest,
    service: WeChatService = Depends()
):
    """获取微信指定子窗口信息"""
    return await service.get_sub_window(nickname=request.nickname, wxname=request.wxname)

@router.post(
    "/getallmessage",
    operation_id="[wx]获取当前窗口加载的消息",
    response_model=APIResponse,
    summary='获取当前窗口加载的消息'
)
async def get_all_message(
    request: GetAllMessageRequest,
    service: WeChatService = Depends()
):
    """获取当前窗口加载的消息"""
    # print('xxxxxxxxxxxxxxxxxxxx')
    return await service.get_all_message(who=request.who, wxname=request.wxname)

@router.post(
    "/gethistorymessage",
    operation_id="[wx]获取历史消息",
    response_model=APIResponse,
    summary='✨获取历史消息'
)
async def get_history_message(
    request: GetHistoryMessageRequest,
    service: WeChatService = Depends()
):
    """获取历史消息"""
    return await service.get_history_message(
        who=request.who,
        n=request.n,
        wxname=request.wxname
    )

@router.post(
    "/sendurlcard",
    operation_id="[wx]发送url卡片",
    response_model=APIResponse,
    summary='✨发送url卡片'
)
async def send_url_card(
    request: SendUrlCardRequest,
    service: WeChatService = Depends()
):
    """微信发送url卡片"""
    return await service.send_url_card(
        url=request.url,
        friends=request.friends,
        timeout=request.timeout,
        wxname=request.wxname
    )

# @router.post(
#     "/addlistenchat",
#     operation_id="[wx]添加监听",
#     response_model=APIResponse,
#     summary="添加监听（需和配合/getnextnewmessage来获取新消息）"
# )
# async def add_listen_chat(
#     request: AddListenChatRequest,
#     service: WeChatService = Depends()
# ):
#     """添加微信子窗口监听"""
#     return await service.add_listen_chat(
#         who=request.who,
#         wxname=request.wxname
#     )

# @router.post(
#     "/removelistenchat",
#     operation_id="[wx]移除监听",
#     response_model=APIResponse,
#     summary="移除监听聊天"
# )
# async def remove_listen_chat(
#     request: RemoveListenChatRequest,
#     service: WeChatService = Depends()
# ):
#     """移除微信子窗口监听"""
#     return await service.remove_listen_chat(
#         who=request.who,
#         wxname=request.wxname
#     )

@router.post(
    "/getnextnewmessage",
    operation_id="[wx]获取下一个新消息",
    response_model=APIResponse,
    summary="获取一个未读消息窗口的新消息"
)
async def get_next_new_message(
    request: GetNextNewMessageRequest,
    service: WeChatService = Depends()
):
    """获取微信下一个新消息"""
    return await service.get_next_new_message(
        filter_mute=request.filter_mute,
        wxname=request.wxname
    )

# @router.post(
#     "/getnewfriends",
#     operation_id="[wx]获取好友申请",
#     response_model=APIResponse,
#     summary='✨获取好友申请列表'
# )
# async def get_new_friends(
#     request: GetNewFriendsRequest,
#     service: WeChatService = Depends()
# ):
#     """获取微信新朋友"""
#     return await service.get_new_friends(
#         acceptable=request.acceptable,
#         wxname=request.wxname
#     )

# @router.post(
#     "/newfriend/accept",
#     operation_id="[wx]接受好友申请",
#     response_model=APIResponse,
#     summary='✨接受好友申请'
# )
# async def accept_new_friend(
#     request: AcceptNewFriendRequest,
#     service: WeChatService = Depends()
# ):
#     """接受微信新朋友"""
#     if isinstance(request.tags, str):
#         tags = [request.tags]
#     else:
#         tags = request.tags
#     return await service.accept_new_friend(
#         new_friend_id=request.new_friend_id,
#         remark=request.remark,
#         tags=tags,
#         wxname=request.wxname
#     )

# @router.post(
#     "/addnewfriend",
#     operation_id="[wx]添加好友",
#     response_model=APIResponse,
#     summary='✨添加新的好友'
# )
# async def add_new_friend(
#     request: AddNewFriendRequest,
#     service: WeChatService = Depends()
# ):
#     """添加新的好友"""
#     return await service.add_new_friend(
#         keywords=request.keywords,
#         addmsg=request.addmsg,
#         remark=request.remark,
#         tags=request.tags,
#         permission=request.permission,
#         timeout=request.timeout,
#         wxname=request.wxname
#     )

@router.post(
    "/group/members/add",
    operation_id="[wx]添加群成员",
    response_model=APIResponse,
    summary="✨向当前或指定群聊添加一个或多个成员"
)
async def add_group_members(
    request: AddGroupMembersRequest,
    service: WeChatService = Depends()
):
    """添加群成员。"""
    return await service.add_group_members(
        who=request.who,
        members=request.members,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/group/create",
    operation_id="[wx]创建群聊",
    response_model=APIResponse,
    summary="✨使用联系人列表创建群聊"
)
async def create_group(
    request: CreateGroupRequest,
    service: WeChatService = Depends()
):
    """创建群聊。"""
    return await service.create_group(
        contacts=request.contacts,
        wxname=request.wxname
    )

@router.post(
    "/group/name",
    operation_id="[wx]修改群聊名称",
    response_model=APIResponse,
    summary="✨修改当前或指定群聊名称"
)
async def set_group_name(
    request: SetGroupNameRequest,
    service: WeChatService = Depends()
):
    """修改群聊名称。"""
    return await service.set_group_name(
        who=request.who,
        value=request.value,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/group/remark",
    operation_id="[wx]修改群聊备注",
    response_model=APIResponse,
    summary="✨修改当前或指定群聊备注"
)
async def set_group_remark(
    request: SetGroupRemarkRequest,
    service: WeChatService = Depends()
):
    """修改群聊备注。"""
    return await service.set_group_remark(
        who=request.who,
        value=request.value,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/group/announcement",
    operation_id="[wx]修改群公告",
    response_model=APIResponse,
    summary="✨修改当前或指定群公告"
)
async def set_group_announcement(
    request: SetGroupAnnouncementRequest,
    service: WeChatService = Depends()
):
    """修改群公告。"""
    return await service.set_group_announcement(
        who=request.who,
        value=request.value,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/group/my-nickname",
    operation_id="[wx]修改群内昵称",
    response_model=APIResponse,
    summary="✨修改我在当前或指定群聊中的昵称"
)
async def set_group_my_nickname(
    request: SetGroupMyNicknameRequest,
    service: WeChatService = Depends()
):
    """修改群内昵称。"""
    return await service.set_group_my_nickname(
        who=request.who,
        value=request.value,
        exact=request.exact,
        wxname=request.wxname
    )

@router.post(
    "/getrecentgroups",
    operation_id="[wx]获取群聊列表",
    response_model=APIResponse,
    summary='✨获取最近群聊列表'
)
async def get_recent_groups(
    request: GetAllRecentGroupsRequest,
    service: WeChatService = Depends()
):
    """获取最近群聊列表"""
    return await service.get_all_recent_groups(wxname=request.wxname)

@router.post(
    "/getfriends",
    operation_id="[wx]获取好友列表",
    response_model=APIResponse,
    summary='✨获取好友详情列表'
)
async def get_friend_details(
    request: GetFriendDetailsRequest,
    service: WeChatService = Depends()
):
    """获取好友详情列表"""
    return await service.get_friend_details(
        n=request.n,
        save_head_image=request.save_head_image,
        wxname=request.wxname
    )

@router.post(
    "/getmyinfo",
    operation_id="[wx]获取我的信息",
    response_model=APIResponse,
    summary='✨获取我的账号信息'
)
async def get_my_info(
    request: GetSessionRequest,
    service: WeChatService = Depends()
):
    """获取我的账号信息"""
    return await service.get_my_info(wxname=request.wxname)

@router.post(
    "/switch/chat",
    operation_id="[wx]切换到聊天页面",
    response_model=APIResponse,
    summary="主窗口切换到聊天页面"
)
async def switch_to_chat_page(
    request: SwitchToChatPageRequest,
    service: WeChatService = Depends()
):
    """切换到聊天页面"""
    return await service.switch_to_chat_page(wxname=request.wxname)

@router.post(
    "/isonline",
    operation_id="[wx]是否在线（掉线）",
    response_model=APIResponse,
    summary="✨微信是否在线（掉线）"
)
async def is_online(
    request: IsOnlineRequest,
    service: WeChatService = Depends()
):
    """微信是否在线"""
    return await service.is_online(wxname=request.wxname)

@router.post(
    "/switch/contact",
    operation_id="[wx]切换到联系人页面",
    response_model=APIResponse,
    summary="主窗口切换到联系人页面"
)
async def switch_to_contact_page(
    request: SwitchToContactPageRequest,
    service: WeChatService = Depends()
):
    """切换到联系人页面"""
    return await service.switch_to_contact_page(wxname=request.wxname)

# @router.post(
#     "/moments",
#     operation_id="[wx]进入朋友圈",
#     response_model=APIResponse,
#     summary='✨进入朋友圈'
# )
# async def moments(
#     request: MomentsRequest,
#     service: WeChatService = Depends()
# ):
#     """进入朋友圈"""
#     return await service.moments(timeout=request.timeout, wxname=request.wxname)

# @router.post(
#     "/publishmoment",
#     operation_id="[wx]发送朋友圈",
#     response_model=APIResponse,
#     summary='✨发送朋友圈'
# )
# async def publish_moment(
#     request: PublishMomentRequest,
#     service: WeChatService = Depends()
# ):
#     """发送朋友圈"""
#     return await service.publish_moment(
#         text=request.text,
#         media_files=request.media_files,
#         privacy=request.privacy,
#         wxname=request.wxname
#     )
