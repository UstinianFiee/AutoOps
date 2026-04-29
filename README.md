# AutoOps — 轻量自动化运维平台

> 面向中小团队的 Docker 应用统一运维平台，核心管理 Docker 服务，不依赖 K8s 与云厂商。

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.10+、FastAPI、SQLAlchemy、MySQL 8.0 |
| 前端 | Vue 3、Vite、Element Plus、Axios |
| 运维核心 | Docker / Docker Compose、Ansible |
| 监控日志 | Prometheus、Grafana、Loki + Promtail、Alertmanager |
| 网关 | Nginx |

## 功能模块

- **仪表盘** — 服务器/应用/部署统计概览
- **服务器管理** — 主机 CRUD、分组、SSH 连通性检测、Ansible 一键初始化
- **应用管理** — 应用 CRUD、绑定服务器、docker-compose 配置管理
- **容器管理** — 容器列表/启停/重启/日志、镜像管理
- **CI/CD 部署** — 手动触发部署、GitLab CI 回调、WebSocket 实时日志、版本回滚
- **监控告警** — Prometheus 指标查询、Grafana 嵌入、Alertmanager 告警
- **日志查询** — Loki LogQL 查询、关键词高亮、多标签筛选
- **用户管理** — 用户 CRUD、角色权限（admin / operator / viewer）

---

## 云服务器部署指南

### 一、服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB | 100 GB SSD |
| 系统 | CentOS 7+ / Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| 带宽 | 1 Mbps | 5 Mbps |

> 推荐云厂商：阿里云 ECS、腾讯云 CVM、华为云 ECS，选择**按量付费**方便测试。

---

### 二、安装 Docker 和 Docker Compose

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker

# 验证
docker --version
docker compose version
```

> 国内服务器如果拉取镜像慢，配置加速器：
> ```bash
> sudo mkdir -p /etc/docker
> sudo tee /etc/docker/daemon.json <<EOF
> {
>   "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
> }
> EOF
> sudo systemctl daemon-reload && sudo systemctl restart docker
> ```

---

### 三、上传项目代码

**方式 A：Git 克隆（推荐）**

```bash
# 服务器上执行
git clone https://github.com/yourname/autoops.git /opt/autoops
cd /opt/autoops
```

**方式 B：本地打包上传**

```bash
# 本地打包
tar -czf autoops.tar.gz --exclude=node_modules --exclude=__pycache__ .

# 上传到服务器（替换为你的 IP）
scp autoops.tar.gz root@YOUR_SERVER_IP:/opt/

# 服务器上解压
ssh root@YOUR_SERVER_IP
mkdir -p /opt/autoops && tar -xzf /opt/autoops.tar.gz -C /opt/autoops
cd /opt/autoops
```

---

### 四、配置环境变量

```bash
cd /opt/autoops
cp backend/.env.example backend/.env
vim backend/.env
```

修改以下关键配置：

```env
# 数据库连接（如果使用云数据库 RDS，填写对应地址）
DATABASE_URL=mysql+pymysql://autoops:yourpassword@127.0.0.1:3306/autoops

# JWT 密钥（务必修改为随机字符串）
SECRET_KEY=your-random-secret-key-at-least-32-chars

# 如果对接 GitLab CI
GITLAB_URL=https://your-gitlab.com
GITLAB_TOKEN=your-gitlab-token
```

---

### 五、一键启动所有服务

```bash
cd /opt/autoops

# 首次启动（会自动构建镜像，约 5-10 分钟）
docker compose up -d --build

# 查看启动状态
docker compose ps

# 查看后端日志
docker compose logs -f backend
```

启动成功后各服务端口：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 Nginx | 80 | 主入口 |
| 后端 FastAPI | 8000 | API 服务 |
| MySQL | 3306 | 数据库（不对外暴露） |
| Prometheus | 9090 | 指标存储 |
| Grafana | 3000 | 监控面板 |
| Alertmanager | 9093 | 告警管理 |
| Loki | 3100 | 日志存储 |
| Node Exporter | 9100 | 主机指标 |

---

### 六、配置云服务器安全组

在云控制台的**安全组/防火墙**中开放以下端口：

| 端口 | 协议 | 用途 | 是否必须 |
|------|------|------|---------|
| 22 | TCP | SSH 登录 | ✅ 必须 |
| 80 | TCP | 前端访问 | ✅ 必须 |
| 8000 | TCP | 后端 API | ✅ 必须 |
| 3000 | TCP | Grafana | 可选 |
| 9090 | TCP | Prometheus | 可选（建议内网） |
| 9093 | TCP | Alertmanager | 可选（建议内网） |

> **安全建议**：9090、9093、3306 等端口不要对公网开放，只允许内网访问。

---

### 七、配置域名（可选）

如果有域名，配置 Nginx 反向代理：

```bash
# 修改 frontend/nginx.conf，将 server_name 改为你的域名
server_name your-domain.com;

# 申请免费 SSL 证书（Let's Encrypt）
apt install certbot python3-certbot-nginx -y
certbot --nginx -d your-domain.com
```

---

### 八、验证部署

```bash
# 检查所有容器状态
docker compose ps

# 测试后端健康检查
curl http://localhost:8000/health

# 测试登录接口
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

浏览器访问 `http://YOUR_SERVER_IP`，使用 `admin / admin123` 登录。

> ⚠️ **首次登录后请立即修改默认密码！**

---

### 九、常用运维命令

```bash
# 查看所有服务状态
docker compose ps

# 重启某个服务
docker compose restart backend

# 查看实时日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止所有服务
docker compose down

# 更新代码后重新部署
git pull
docker compose up -d --build backend frontend

# 清理无用镜像
docker image prune -f

# 备份数据库
docker compose exec mysql mysqldump -uautoops -pautoops123 autoops > backup_$(date +%Y%m%d).sql
```

---

### 十、使用云数据库 RDS（推荐生产环境）

生产环境建议使用云厂商的 RDS MySQL，避免数据丢失：

1. 在云控制台创建 MySQL 8.0 实例
2. 创建数据库 `autoops`，创建用户并授权
3. 修改 `backend/.env`：
   ```env
   DATABASE_URL=mysql+pymysql://autoops:password@rds-xxx.mysql.rds.aliyuncs.com:3306/autoops
   ```
4. 修改 `docker-compose.yml`，注释掉 `mysql` 服务，删除 backend 对 mysql 的 `depends_on`
5. 重新启动：`docker compose up -d --build`

---

### 十一、项目结构

```
autoops/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口，自动建表
│   │   ├── models.py       # 数据库模型（5张表）
│   │   ├── schemas.py      # Pydantic 数据模型
│   │   ├── security.py     # JWT 认证 + 权限控制
│   │   └── routers/        # 路由模块（9个）
│   ├── ansible/            # Ansible Playbook
│   │   ├── init_server.yml # 服务器初始化
│   │   └── deploy_app.yml  # 应用部署
│   └── Dockerfile
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── views/          # 8个页面
│   │   ├── layouts/        # 主布局
│   │   ├── stores/         # Pinia 状态
│   │   ├── router/         # 路由
│   │   └── api/            # Axios 封装
│   └── Dockerfile
├── monitoring/             # 监控配置
│   ├── prometheus/         # 指标采集 + 告警规则
│   ├── alertmanager/       # 告警路由
│   ├── grafana/            # 面板 + 数据源
│   ├── loki/               # 日志存储
│   └── promtail/           # 日志采集
├── scripts/                # 工具脚本
│   └── start.sh            # 一键启动
└── docker-compose.yml      # 服务编排
```

---

### 十二、GitLab CI 集成

在被管理项目的 `.gitlab-ci.yml` 中添加：

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_PROJECT_NAME:$CI_COMMIT_SHORT_SHA .
    - docker push registry.example.com/$CI_PROJECT_NAME:$CI_COMMIT_SHORT_SHA

deploy:
  stage: deploy
  script:
    - |
      curl -X POST http://YOUR_AUTOOPS_IP/api/deploy/ci-callback \
        -H "Content-Type: application/json" \
        -d "{
          \"app_name\": \"$CI_PROJECT_NAME\",
          \"commit_sha\": \"$CI_COMMIT_SHA\",
          \"version\": \"$CI_COMMIT_REF_NAME\",
          \"status\": \"success\"
        }"
  only:
    - main
```

---

*AutoOps v1.0 · 2026*
