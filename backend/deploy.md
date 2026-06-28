# 服务器部署教程

## 推荐配置

| 项目 | 推荐 | 最低 |
|------|------|------|
| CPU | 2核 | 1核 |
| 内存 | 4G | 2G |
| 硬盘 | 40G SSD | 20G |
| 系统 | Ubuntu 22.04 / CentOS 8 | — |
| 参考价格 | **68元/月**（阿里云/腾讯云轻量应用服务器） | — |

## 方案一：Docker 一键部署（推荐）

### 1. 连接服务器

```bash
ssh root@你的服务器IP
```

### 2. 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | bash
apt install docker-compose -y

# CentOS
curl -fsSL https://get.docker.com | bash
yum install docker-compose -y
```

### 3. 上传项目

```bash
# 在本地电脑执行（把项目传到服务器）
scp -r D:\西南大王后端 root@你的服务器IP:/opt/xinan-dawang/
```

### 4. 配置环境变量

在服务器上：

```bash
cd /opt/xinan-dawang
cp .env.example .env
nano .env   # 填入你的配置
```

**至少需要修改：**
- `SECRET_KEY` — 改为随机字符串
- `DEEPSEEK_API_KEY` — 填入你的 API Key（AI陪聊必须）

### 5. 启动

```bash
docker-compose up -d
```

### 6. 验证

访问 `http://你的服务器IP:8000/health`

---

## 方案二：直接部署（不用 Docker）

### 1. 服务器安装 Python

```bash
apt update && apt install python3 python3-pip -y
```

### 2. 上传项目

```bash
scp -r D:\西南大王后端 root@你的服务器IP:/opt/xinan-dawang/
```

### 3. 安装依赖

```bash
cd /opt/xinan-dawang
pip install -r requirements.txt
```

### 4. 配置 .env

```bash
cp .env.example .env
nano .env
```

### 5. 使用 systemd 作为后台服务

```bash
nano /etc/systemd/system/xinan-dawang.service
```

写入：

```ini
[Unit]
Description=西南大王后端服务
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/xinan-dawang
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

然后：

```bash
systemctl daemon-reload
systemctl enable xinan-dawang
systemctl start xinan-dawang
systemctl status xinan-dawang   # 查看状态
```

---

## 配置 Nginx 反向代理（可选）

如需域名访问或 HTTPS：

```bash
apt install nginx -y
```

```nginx
server {
    listen 80;
    server_name 你的域名.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 上传文件大小限制
    client_max_body_size 50m;
}
```

HTTPS 证书可以用 `certbot` 免费获取：

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d 你的域名.com
```

---

## 数据备份

数据库和上传文件在：
- Docker 方案：`/opt/xinan-dawang/data/` 和 `/opt/xinan-dawang/uploads/`
- 直接部署：`/opt/xinan-dawang/` 下的 `.db` 文件和 `uploads/` 目录

建议设置 crontab 每天备份：

```bash
# 每天凌晨3点备份
0 3 * * * tar -czf /backup/xinan-dawang-$(date +\%Y\%m\%d).tar.gz /opt/xinan-dawang/data/ /opt/xinan-dawang/uploads/
```
