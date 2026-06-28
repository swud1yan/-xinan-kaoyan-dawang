# 西南大王后端

西南考研大王 App 的后端服务，基于 **FastAPI + SQLite**。

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (Python 3.12+) |
| 数据库 | SQLite (通过 SQLAlchemy + aiosqlite 异步驱动) |
| 认证 | JWT (python-jose) + bcrypt 密码哈希 |
| LLM 接入 | DeepSeek / 通义千问 / Claude 三选一 |
| 文件存储 | 本地磁盘 (uploads 目录) |

## 快速开始

### 1. 安装 Python 依赖

```bash
cd D:\西南大王后端
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
copy .env.example .env
```

然后编辑 `.env` 文件，填入必要配置。

### 3. 启动服务

```bash
python -m app.main
```

服务启动后访问：
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## ⚠️ 需要你自行配置的内容

### 必须：LLM API 密钥（AI 陪聊功能）

AI 陪聊功能需要接入大语言模型。你需要在以下三个中**至少选一个**注册并获取 API Key：

| 提供商 | 注册地址 | 价格参考 | 推荐 |
|--------|----------|----------|------|
| **DeepSeek** | https://platform.deepseek.com/api_keys | 极低（1元≈100万token） | ⭐ 推荐 |
| 通义千问 | https://dashscope.console.aliyun.com/apiKey | 中等 | |
| Claude | https://console.anthropic.com/ | 较高 | |

获取 API Key 后，在 `.env` 文件中填入相应配置：

```env
# 如果用 DeepSeek（推荐）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_PROVIDER=deepseek

# 如果用通义千问
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_PROVIDER=dashscope

# 如果用 Claude
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
LLM_PROVIDER=anthropic
```

### 可选：推送通知

如果需要推送通知（报名提醒、分数线变动），需要配置 Firebase Cloud Messaging：

1. 去 https://console.firebase.google.com/ 创建项目
2. 获取 Server Key
3. 在 `.env` 中填入 `FCM_SERVER_KEY=...`

目前代码中推送功能**仅预留了接口位置**，需要你确认是否需要完整实现。

### 可选：分数线实时爬取

目前分数线数据使用**内置种子数据**（重庆大学、电子科大、四川大学、西南大学、重庆邮电大学，2022-2025年）。

如需实现实时爬取，需要：
1. 分析目标网站（研招网或各院校研究生院）的 HTML 结构
2. 修改 `app/services/scraper.py` 中的解析逻辑
3. 配置定时任务触发爬取

---

## API 接口总览

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| GET | `/auth/me` | 获取当前用户 |

### AI 陪聊
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat/send` | 发送消息 |
| GET | `/chat/history` | 聊天历史 |
| DELETE | `/chat/history` | 清空历史 |

### 研友圈
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/posts` | 帖子列表（分页、标签筛选） |
| POST | `/posts` | 发帖 |
| DELETE | `/posts/{id}` | 删帖 |
| GET | `/posts/{id}/comments` | 评论列表 |
| POST | `/posts/{id}/comments` | 发表评论 |
| POST | `/posts/{id}/likes` | 点赞/取消 |

### 分数线
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/score-lines/schools` | 院校列表 |
| GET | `/score-lines/programs?school=` | 某校专业列表 |
| GET | `/score-lines?school=&program=` | 历年分数线 |

### 真题
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/exam-papers` | 真题列表 |
| GET | `/exam-papers/subjects` | 科目列表 |
| GET | `/exam-papers/years` | 年份列表 |
| POST | `/exam-papers/upload` | 上传真题 |
| GET | `/exam-papers/download/{filename}` | 下载真题 |

---

## 前端对接

前端 Flutter 项目中的 base URL 应配置为：

```dart
// 模拟器用 10.0.2.2，真机用电脑局域网 IP
const baseUrl = 'http://localhost:8000';
```

前端已有的 `http` 包可直接使用，代码中标记了 `⚠️ 后端接入点` 的位置，对照上面的 API 路径接入即可。

---

## 项目结构

```
D:\西南大王后端\
├── app/
│   ├── main.py              # 应用入口 + FastAPI 配置
│   ├── config.py            # 环境变量配置
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 数据模型
│   │   ├── user.py          # 用户
│   │   ├── post.py          # 帖子 / 评论 / 点赞
│   │   ├── score_line.py    # 分数线
│   │   ├── exam_paper.py    # 真题
│   │   └── chat.py          # 聊天记录
│   ├── routers/             # API 路由
│   │   ├── auth.py          # 认证
│   │   ├── chat.py          # AI 陪聊
│   │   ├── posts.py         # 研友圈
│   │   ├── score_lines.py   # 分数线
│   │   └── exam_papers.py   # 真题
│   ├── services/            # 业务逻辑
│   │   ├── auth_service.py  # 登录/注册
│   │   ├── chat_service.py  # LLM 调用
│   │   ├── post_service.py  # 帖子 CRUD
│   │   └── scraper.py       # 数据爬取 + 种子数据
│   └── utils/
│       └── security.py      # JWT + 密码哈希
├── uploads/                 # 真题文件存储
├── requirements.txt
├── .env.example
└── README.md
```
