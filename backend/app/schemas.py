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
class AppCreate(BaseModel):
    name: str
    git_url: Optional[str] = None
    branch: str = "main"
    server_id: Optional[int] = None
    compose_content: Optional[str] = None
    deploy_path: str = "/opt/apps"
    remark: Optional[str] = None


class AppUpdate(BaseModel):
    git_url: Optional[str] = None
    branch: Optional[str] = None
    server_id: Optional[int] = None
    compose_content: Optional[str] = None
    deploy_path: Optional[str] = None
    remark: Optional[str] = None


class AppOut(BaseModel):
    id: int
    name: str
    git_url: Optional[str]
    branch: str
    server_id: Optional[int]
    compose_content: Optional[str]
    deploy_path: str
    status: str
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── DeployRecord ──────────────────────────────────────
class DeployRecordOut(BaseModel):
    id: int
    app_id: int
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
