# wxautox4 RESTful API

基于 FastAPI 开发的 HTTP API 服务，为 wxautox4 提供完整的 RESTful API 接口。支持消息发送、群管理、好友管理等微信自动化功能。

### 安装依赖

```bash
# 安装wxautox4
pip install wxautox4

# 或使用requirements.txt
pip install -r requirements.txt
```

> [!NOTE]
> 本项目专门为wxautox4设计，需要wxautox4 Plus版本

> [!IMPORTANT]
> **激活要求**：wxautox4需要激活后才能使用。请先使用以下方式激活：
> ```bash
> # 检查激活状态
> wxautox4 -k
>
> # 激活
> wxautox4 -a your-activation-code
> ```

## 配置管理

### 配置文件
项目使用 `config.yaml` 作为主配置文件，所有服务器设置都通过此文件管理：

```yaml
server:
  host: "0.0.0.0"  # 服务器监听地址
  port: 8000       # 服务器监听端口
  reload: true     # 是否启用热重载

auth:
  token: "your-secret-token-here"  # API认证密钥

database:
  type: "sqlite"  # 数据库类型
  sqlite:
    path: "./data/wxautox.db"  # SQLite数据库路径
```

### 手动模式
```bash
# 启动服务（使用配置文件中的设置）
python run.py

# 或使用uvicorn直接启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 文档

### API 文档
启动服务后，可以通过以下地址访问交互式 API 文档：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 项目文档
- [API 响应格式规范](docs/API_RESPONSE_FORMAT.md) - 详细的 API 响应格式说明

## 快速开始

### 1. 安装依赖

```bash
# 安装 wxautox4（需要 Plus 版本）
pip install wxautox4

# 或使用项目配置
uv sync
```

### 2. 激活 wxautox4

```bash
# 检查激活状态
wxautox4 -k

# 激活 wxautox4
wxautox4 -a your-activation-code
```

> **重要**: wxautox4 需要激活后才能使用

### 3. 配置服务

编辑 `config.yaml` 文件：

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  reload: true

auth:
  token: "your-secret-token-here"  # 修改为你的 token
```

### 4. 启动服务

```bash
# 使用 bat 脚本启动（Windows）
run.bat

# 使用 Python 启动
python run.py

# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

## API 接口

所有接口都遵循统一的响应格式，详见 [API 响应格式规范](docs/API_RESPONSE_FORMAT.md)。

### 微信功能接口

#### 初始化
- `POST /api/v1/wechat/initialize` - 初始化微信实例
- `GET /api/v1/wechat/status` - 获取微信状态

#### 消息功能
- `POST /api/v1/wechat/send` - 发送消息
- `POST /api/v1/wechat/sendfile` - 发送文件
- `POST /api/v1/wechat/sendurlcard` - 发送 URL 卡片
- `POST /api/v1/wechat/getallmessage` - 获取当前窗口消息
- `POST /api/v1/wechat/gethistorymessage` - 获取历史消息
- `POST /api/v1/wechat/getnextnewmessage` - 获取新消息

#### 会话管理
- `POST /api/v1/wechat/getsession` - 获取会话列表
- `POST /api/v1/wechat/getsubwindow` - 获取指定子窗口
- `POST /api/v1/wechat/getallsubwindow` - 获取所有子窗口
- `POST /api/v1/wechat/chatwith` - 切换聊天窗口

#### 好友管理
- `POST /api/v1/wechat/getfriends` - 获取好友列表
- `POST /api/v1/wechat/getmyinfo` - 获取我的信息

#### 群聊管理
- `POST /api/v1/wechat/getrecentgroups` - 获取群聊列表

#### 页面控制
- `POST /api/v1/wechat/switch/chat` - 切换到聊天页面
- `POST /api/v1/wechat/switch/contact` - 切换到联系人页面
- `POST /api/v1/wechat/isonline` - 检查在线状态

### 聊天接口
- `POST /api/v1/chat/send` - 子窗口发送消息
- `POST /api/v1/chat/getallmessage` - 获取子窗口所有消息
- `POST /api/v1/chat/getnewmessage` - 获取子窗口新消息
- `POST /api/v1/chat/msg/quote` - 发送引用消息
- `POST /api/v1/chat/close` - 关闭子窗口

### 监听接口
- `POST /api/v1/listen/start` - 启动监听
- `POST /api/v1/listen/stop` - 停止监听
- `GET /api/v1/listen/status` - 获取监听状态
- `POST /api/v1/listen/batch/start` - 批量启动监听
- `GET /api/v1/listen/config` - 获取配置

### 文件管理接口
- `POST /api/v1/files/upload` - 上传文件
- `GET /api/v1/files/{file_id}` - 获取文件信息
- `DELETE /api/v1/files/{file_id}` - 删除文件
- `GET /api/v1/files/` - 获取文件列表

### 激活接口
- `POST /api/v1/activation/activate` - 激活许可证
- `GET /api/v1/activation/check` - 检查激活状态

### 信息接口
- `GET /api/v1/info/package` - 获取包信息

## 认证

所有 API 请求都需要在 Header 中包含有效的认证 token：

```http
Authorization: Bearer <your-token>
```

配置你的 token 在 `config.yaml` 中：

```yaml
auth:
  token: "your-secret-token-here"
```

## 响应格式

所有 API 接口都遵循统一的响应格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 返回数据
  }
}
```

### 常见响应类型

#### 列表数据
```json
{
  "success": true,
  "message": "",
  "data": {
    "total": 100,
    "items": [...]
  }
}
```

#### 单个对象
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "item": {...}
  }
}
```

#### 错误响应
```json
{
  "success": false,
  "message": "操作失败",
  "data": {
    "error_code": "ERROR_CODE",
    "solution": "解决方案"
  }
}
```

详见 [API 响应格式规范文档](docs/API_RESPONSE_FORMAT.md)

## 配置说明

### 主要配置文件
- `config.yaml` - 主配置文件（包含所有服务器设置）
- `pyproject.toml` - 项目依赖配置

### 重要配置项
- `server.port` - 服务端口（默认8000）
- `server.host` - 服务器监听地址（默认0.0.0.0）
- `server.reload` - 热重载开关（默认true）
- `auth.token` - API访问令牌
- `database.type` - 数据库类型（默认sqlite）
