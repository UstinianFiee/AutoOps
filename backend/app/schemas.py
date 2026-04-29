from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ── User ──────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    email: Optional[str] = None


class UserUpdate(BaseModel):
    role: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    email: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Server ────────────────────────────────────────────
class ServerCreate(BaseModel):
    name: str
    ip: str
    port: int = 22
    username: str = "root"
    auth_type: str = "password"
    password: Optional[str] = None
    private_key: Optional[str] = None
    group: str = "default"
    remark: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    auth_type: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    group: Optional[str] = None
    remark: Optional[str] = None


class ServerOut(BaseModel):
    id: int
    name: str
    ip: str
    port: int
    username: str
    auth_type: str
    group: str
    status: str
    os_info: Optional[str]
    cpu_cores: Optional[int]
    memory_gb: Optional[int]
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── App ───────────────────────────────────────────────
import os as _os

FORBIDDEN_PATHS = {"/", "/etc", "/bin", "/sbin", "/usr", "/lib", "/lib64",
                   "/boot", "/dev", "/proc", "/sys", "/run", "/var/run", "/tmp"}

def _validate_deploy_path(path: str) -> str:
    path = path.strip()
    if not path.startswith("/"):
        raise ValueError("部署路径必须是绝对路径")
    normalized = _os.path.normpath(path)
    if normalized in FORBIDDEN_PATHS:
        raise ValueError(f"禁止部署到系统关键目录: {normalized}")
    return normalized


class AppCreate(BaseModel):
    name: str
    source_type: str = "git"
    git_url: Optional[str] = None
    branch: str = "main"
    git_token: Optional[str] = None
    server_id: Optional[int] = None
    compose_content: Optional[str] = None
    deploy_path: str = "/opt/apps"
    remark: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        self.deploy_path = _validate_deploy_path(self.deploy_path)


class AppUpdate(BaseModel):
    git_url: Optional[str] = None
    branch: Optional[str] = None
    git_token: Optional[str] = None
    server_id: Optional[int] = None
    compose_content: Optional[str] = None
    deploy_path: Optional[str] = None
    remark: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.deploy_path:
            self.deploy_path = _validate_deploy_path(self.deploy_path)


class AppOut(BaseModel):
    id: int
    name: str
    source_type: str
    git_url: Optional[str]
    branch: str
    server_id: Optional[int]
    compose_content: Optional[str]
    deploy_path: str
    has_token: bool = False
    webhook_secret: Optional[str] = None
    status: str
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── DeployRecord ──────────────────────────────────────
class DeployRecordOut(BaseModel):
    id: int
    app_id: int
    server_id: Optional[int]
    version: Optional[str]
    commit_sha: Optional[str]
    status: str
    trigger: str
    log: Optional[str]
    operator: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeployRequest(BaseModel):
    app_id: int
    server_id: int                    # 必须指定目标服务器
    version: Optional[str] = None
    branch: Optional[str] = None


class RollbackRequest(BaseModel):
    record_id: int


# ── Task ──────────────────────────────────────────────
class TaskOut(BaseModel):
    id: int
    server_id: Optional[int]
    task_type: str
    target_hosts: Optional[str]
    params: Optional[Any]
    status: str
    output: Optional[str]
    operator: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────
class DashboardStats(BaseModel):
    total_servers: int
    online_servers: int
    total_apps: int
    running_apps: int
    total_deploys: int
    success_deploys: int
    recent_deploys: List[DeployRecordOut]
