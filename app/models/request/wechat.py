from pydantic import BaseModel
from typing import Optional, List, Union

# 基础请求
class BaseRequest(BaseModel):
    wxname: Union[None, str] = ''

# 基础聊天请求
class BaseChatRelevantRequest(BaseRequest):
    who: str = '文件传输助手'
    exact: bool = False

# 发送消息请求
class SendMessageRequest(BaseChatRelevantRequest):
    msg: str
    clear: bool = True
    at: Union[str, List[str]] = ''

# 切换聊天窗口
class ChatWithRequest(BaseChatRelevantRequest):
    pass

# 获取聊天窗口信息
class ChatInfoRequest(BaseRequest):
    who: Optional[str] = None
    exact: bool = False

# 发送文件请求
class SendFileRequest(BaseChatRelevantRequest):
    file_id: str  # 文件ID，对应上传的文件

# 发送url卡片请求
class SendUrlCardRequest(BaseRequest):
    url: str = 'https://plus.wxauto.org'
    friends: Union[str, List[str]] = '文件传输助手'
    timeout: int = 10

# 获取子窗口请求
class GetAllSubWindowRequest(BaseRequest):
    pass

# 添加监听聊天请求
class AddListenChatRequest(BaseRequest):
    who: str = '文件传输助手'

# 获取下一个新消息请求
class GetNextNewMessageRequest(BaseRequest):
    filter_mute: bool = False

# 获取所有消息请求
class GetAllMessageRequest(BaseRequest):
    who: str = '文件传输助手'

# 根据id发送引用消息
class SendQuoteByIdRequest(BaseRequest):
    msg_id: str
    content: str

# 获取新朋友请求
class GetNewFriendsRequest(BaseRequest):
    acceptable: bool = True

# 接受新朋友请求
class AcceptNewFriendRequest(BaseRequest):
    new_friend_id: str
    remark: str = None
    tags: Union[List[str], str, None] = None

# 切换到聊天页面请求
class SwitchToChatPageRequest(BaseRequest):
    pass

# 切换到联系人页面请求
class SwitchToContactPageRequest(BaseRequest):
    pass

class IsOnlineRequest(BaseRequest):
    pass

# 获取会话列表请求
class GetSessionRequest(BaseRequest):
    pass

# 获取子窗口请求
class GetSubWindowRequest(BaseRequest):
    nickname: str

# 移除监听请求
class RemoveListenChatRequest(BaseRequest):
    who: str

# 获取历史消息请求
class GetHistoryMessageRequest(BaseChatRelevantRequest):
    n: int = 50

# 获取群聊列表请求
class GetAllRecentGroupsRequest(BaseRequest):
    pass

# 群聊目标请求
class BaseGroupRequest(BaseRequest):
    who: Optional[str] = None
    exact: bool = False

# 添加群成员
class AddGroupMembersRequest(BaseGroupRequest):
    members: Union[str, List[str]]

# 创建群聊
class CreateGroupRequest(BaseRequest):
    contacts: List[str]

# 修改群聊字段
class SetGroupValueRequest(BaseGroupRequest):
    value: str

class SetGroupNameRequest(SetGroupValueRequest):
    pass

class SetGroupRemarkRequest(SetGroupValueRequest):
    pass

class SetGroupAnnouncementRequest(SetGroupValueRequest):
    pass

class SetGroupMyNicknameRequest(SetGroupValueRequest):
    pass

# 获取好友列表请求
class GetFriendDetailsRequest(BaseRequest):
    n: Optional[int] = None
    save_head_image: bool = False

# 添加好友请求
class AddNewFriendRequest(BaseRequest):
    keywords: str
    addmsg: Optional[str] = None
    remark: Optional[str] = None
    tags: Optional[List[str]] = None
    permission: str = '朋友圈'
    timeout: int = 5

# 发送朋友圈请求
class PublishMomentRequest(BaseRequest):
    text: str
    media_files: Optional[List[str]] = None
    privacy: Optional[dict] = None

# 进入朋友圈请求
class MomentsRequest(BaseRequest):
    timeout: int = 3
