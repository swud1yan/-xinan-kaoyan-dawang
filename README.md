# 西南考研大王 (Xinan Dawang)

西南考研大王是一款考研备考助手 App，帮助考生高效备战研究生考试。

## 项目结构

```
xinan-kaoyan-dawang/
├── frontend/          # Flutter 前端 App (Android, iOS, Web, Desktop)
├── backend/           # FastAPI 后端服务 (Python)
└── README.md
```

## 技术栈

### 前端
- **框架**: Flutter (Dart)
- **平台**: Android / iOS / Web / Windows / macOS / Linux

### 后端
- **框架**: FastAPI (Python 3.12+)
- **数据库**: SQLite (SQLAlchemy + aiosqlite)
- **认证**: JWT + bcrypt
- **部署**: Docker

## 功能模块

- 📚 考研真题练习与解析
- 🤖 AI 智能陪聊（支持 DeepSeek / 通义千问 / Claude）
- 📊 学习进度追踪与番茄钟
- 🏫 院校分数线查询
- 👥 好友系统与排行榜
- 🎴 闪卡记忆
- 📝 错题本与日记
- 🪙 积分与兑换系统

## 快速开始

### 后端
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 编辑 .env 填入配置
python -m app.main
```

### 前端
```bash
cd frontend
flutter pub get
flutter run
```

## 环境要求

- Flutter SDK 3.x+
- Python 3.12+
- Docker (可选)
