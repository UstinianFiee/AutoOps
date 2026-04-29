from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(16), default="viewer")  # admin / operator / viewer
    email = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Server(Base):
    __tablename__ = "server"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    ip = Column(String(64), nullable=False, unique=True)
    port = Column(Integer, default=22)
    username = Column(String(64), default="root")
    auth_type = Column(String(16), default="password")  # password / key
    password = Column(String(256), nullable=True)
    private_key = Column(Text, nullable=True)
    group = Column(String(64), default="default")
    status = Column(String(16), default="unknown")  # online / offline / unknown
    os_info = Column(String(256), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    memory_gb = Column(Integer, nullable=True)
    remark = Column(String(256), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    tasks = relationship("Task", back_populates="server")
    apps = relationship("App", back_populates="server")


class App(Base):
    __tablename__ = "app"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True)

    # 代码来源：git / upload
    source_type = Column(String(16), default="git")

    # Git 来源字段
    git_url = Column(String(512), nullable=True)
    branch = Column(String(64), default="main")
    git_token = Column(String(512), nullable=True)   # 加密存储的 Token

    # 上传来源字段
    upload_path = Column(String(512), nullable=True)  # 服务端存储路径

    # 部署配置
    server_id = Column(Integer, ForeignKey("server.id"), nullable=True)
    compose_content = Column(Text, nullable=True)
    deploy_path = Column(String(256), default="/opt/apps")

    # Webhook
    webhook_secret = Column(String(128), nullable=True)  # 用于验证 webhook 签名

    status = Column(String(16), default="stopped")  # running / stopped / deploying
    remark = Column(String(256), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    server = relationship("Server", back_populates="apps")
    deploy_records = relationship("DeployRecord", back_populates="app")


class DeployRecord(Base):
    __tablename__ = "deploy_record"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("app.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("server.id"), nullable=True)  # 部署目标服务器
    version = Column(String(128), nullable=True)
    commit_sha = Column(String(64), nullable=True)
    status = Column(String(16), default="pending")  # pending / precheck / running / success / failed
    trigger = Column(String(16), default="manual")  # manual / webhook
    log = Column(Text, nullable=True)
    operator = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

    app = relationship("App", back_populates="deploy_records")


class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("server.id"), nullable=True)
    task_type = Column(String(64), nullable=False)  # init / ping / playbook / shell
    target_hosts = Column(String(256), nullable=True)
    params = Column(JSON, nullable=True)
    status = Column(String(16), default="pending")  # pending / running / success / failed
    output = Column(Text, nullable=True)
    operator = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

    server = relationship("Server", back_populates="tasks")
