from __future__ import annotations
import os, secrets, hashlib, hmac, zipfile, tarfile, shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, require_operator

router = APIRouter(prefix="/api/apps", tags=["应用管理"])

# 上传文件存储目录（容器内）
UPLOAD_DIR = "/tmp/autoops_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的压缩包格式
ALLOWED_EXTENSIONS = {".zip", ".tar.gz", ".tgz", ".tar.bz2"}
# 最大上传大小：200MB
MAX_UPLOAD_SIZE = 200 * 1024 * 1024

# Token 加密密钥（从环境变量读，生产环境必须设置）
_TOKEN_KEY = os.environ.get("TOKEN_ENCRYPT_KEY", "autoops-token-key-change-in-prod")


def _encrypt_token(token: str) -> str:
    """简单对称加密 Token（XOR + hex，生产建议用 Fernet）"""
    key = hashlib.sha256(_TOKEN_KEY.encode()).digest()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(token.encode()))
    return encrypted.hex()


def _decrypt_token(encrypted_hex: str) -> str:
    key = hashlib.sha256(_TOKEN_KEY.encode()).digest()
    encrypted = bytes.fromhex(encrypted_hex)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted)).decode()


def _build_git_url_with_token(git_url: str, token: str) -> str:
    """将 Token 注入 Git URL（支持 GitHub/Gitee/GitLab）"""
    if not token:
        return git_url
    if git_url.startswith("https://"):
        return git_url.replace("https://", f"https://{token}@", 1)
    return git_url


def _validate_zip_no_traversal(file_path: str) -> bool:
    """检查压缩包内是否有路径穿越风险"""
    try:
        if file_path.endswith(".zip"):
            with zipfile.ZipFile(file_path) as zf:
                for name in zf.namelist():
                    if ".." in name or name.startswith("/"):
                        return False
        elif any(file_path.endswith(ext) for ext in [".tar.gz", ".tgz", ".tar.bz2"]):
            with tarfile.open(file_path) as tf:
                for member in tf.getmembers():
                    if ".." in member.name or member.name.startswith("/"):
                        return False
        return True
    except Exception:
        return False


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[schemas.AppOut])
def list_apps(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    apps = db.query(models.App).all()
    result = []
    for app in apps:
        data = schemas.AppOut.model_validate(app)
        # has_token 不在 ORM 里，手动注入
        result.append(data.model_copy(update={"has_token": bool(app.git_token)}))
    return result


@router.post("", response_model=schemas.AppOut)
def create_app(
    body: schemas.AppCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    if db.query(models.App).filter(models.App.name == body.name).first():
        raise HTTPException(status_code=400, detail="应用名已存在")

    # 校验 Git 来源必须有 URL
    if body.source_type == "git" and not body.git_url:
        raise HTTPException(status_code=400, detail="Git 来源必须填写仓库地址")

    data = body.model_dump()
    # 加密存储 Token
    if data.get("git_token"):
        data["git_token"] = _encrypt_token(data["git_token"])
    # 生成 Webhook Secret
    data["webhook_secret"] = secrets.token_hex(24)

    app = models.App(**data)
    db.add(app)
    db.commit()
    db.refresh(app)

    out = schemas.AppOut.model_validate(app)
    return out.model_copy(update={"has_token": bool(app.git_token)})


@router.get("/{app_id}", response_model=schemas.AppOut)
def get_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    out = schemas.AppOut.model_validate(app)
    return out.model_copy(update={"has_token": bool(app.git_token)})


@router.put("/{app_id}", response_model=schemas.AppOut)
def update_app(
    app_id: int,
    body: schemas.AppUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    data = body.model_dump(exclude_none=True)
    if "git_token" in data and data["git_token"]:
        data["git_token"] = _encrypt_token(data["git_token"])
    elif "git_token" in data and not data["git_token"]:
        data["git_token"] = None  # 清空 token

    for k, v in data.items():
        setattr(app, k, v)
    db.commit()
    db.refresh(app)

    out = schemas.AppOut.model_validate(app)
    return out.model_copy(update={"has_token": bool(app.git_token)})


@router.delete("/{app_id}")
def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    # 清理上传文件
    if app.upload_path and os.path.exists(app.upload_path):
        try:
            shutil.rmtree(app.upload_path, ignore_errors=True)
        except Exception:
            pass
    db.query(models.DeployRecord).filter(models.DeployRecord.app_id == app_id).delete()
    db.delete(app)
    db.commit()
    return {"message": "删除成功"}


# ── 文件上传 ──────────────────────────────────────────────────────────────────

@router.post("/{app_id}/upload")
async def upload_source(
    app_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    """上传本地压缩包作为应用代码来源"""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    if app.source_type != "upload":
        raise HTTPException(status_code=400, detail="该应用不是上传来源类型")

    # 校验文件名和扩展名
    filename = file.filename or ""
    ext = ""
    for allowed in ALLOWED_EXTENSIONS:
        if filename.endswith(allowed):
            ext = allowed
            break
    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，仅允许: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 读取并校验大小
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大，最大允许 {MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    # 保存到临时目录
    app_upload_dir = os.path.join(UPLOAD_DIR, f"app_{app_id}")
    os.makedirs(app_upload_dir, exist_ok=True)
    save_path = os.path.join(app_upload_dir, f"source{ext}")

    with open(save_path, "wb") as f:
        f.write(content)

    # 校验压缩包内无路径穿越
    if not _validate_zip_no_traversal(save_path):
        os.unlink(save_path)
        raise HTTPException(status_code=400, detail="压缩包包含不安全的路径，拒绝上传")

    # 更新应用的上传路径
    app.upload_path = save_path
    db.commit()

    return {
        "message": "上传成功",
        "filename": filename,
        "size_mb": round(len(content) / 1024 / 1024, 2),
        "path": save_path,
    }


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.post("/webhook/{webhook_secret}")
async def webhook_trigger(
    webhook_secret: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """接收 GitHub/Gitee Webhook，自动触发部署"""
    app = db.query(models.App).filter(
        models.App.webhook_secret == webhook_secret
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Webhook 地址无效")

    body = await request.body()

    # 验证 GitHub Webhook 签名（X-Hub-Signature-256）
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if sig_header:
        expected = "sha256=" + hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=401, detail="Webhook 签名验证失败")

    # 解析推送事件
    import json
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")

    # 提取分支信息
    ref = payload.get("ref", "")
    pushed_branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ""
    commit_sha = payload.get("after", "") or payload.get("head_commit", {}).get("id", "")

    # 只处理目标分支的推送
    if pushed_branch and pushed_branch != app.branch:
        return {"message": f"忽略分支 {pushed_branch}，目标分支为 {app.branch}"}

    # 必须绑定了服务器才能自动部署
    if not app.server_id:
        return {"message": "应用未绑定服务器，跳过自动部署"}

    # 创建部署记录并触发
    record = models.DeployRecord(
        app_id=app.id,
        server_id=app.server_id,
        version=pushed_branch or app.branch,
        commit_sha=commit_sha[:12] if commit_sha else None,
        status="pending",
        trigger="webhook",
        operator="webhook",
    )
    db.add(record)
    app.status = "deploying"
    db.commit()
    db.refresh(record)

    from app.config import settings
    import threading
    threading.Thread(
        target=_trigger_deploy_bg,
        args=(record.id, settings.DATABASE_URL),
        daemon=True
    ).start()

    return {"message": "Webhook 已接收，部署已触发", "record_id": record.id}


@router.get("/{app_id}/webhook-info")
def get_webhook_info(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    """获取应用的 Webhook 配置信息"""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/apps/webhook/{app.webhook_secret}"

    return {
        "webhook_url": webhook_url,
        "secret": app.webhook_secret,
        "events": ["push"],
        "content_type": "application/json",
        "tip": "在 GitHub/Gitee 仓库设置 → Webhooks 中添加此地址",
    }


@router.post("/{app_id}/regenerate-webhook")
def regenerate_webhook(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    """重新生成 Webhook Secret"""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    app.webhook_secret = secrets.token_hex(24)
    db.commit()
    return {"message": "Webhook Secret 已重新生成", "secret": app.webhook_secret}


# ── 状态操作 ──────────────────────────────────────────────────────────────────

@router.post("/{app_id}/start")
def start_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    app.status = "running"
    db.commit()
    return {"message": f"应用 {app.name} 已启动"}


@router.post("/{app_id}/stop")
def stop_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    app.status = "stopped"
    db.commit()
    return {"message": f"应用 {app.name} 已停止"}


def _trigger_deploy_bg(record_id: int, db_url: str):
    """Webhook 触发的部署，复用 deploy.py 的逻辑"""
    from app.routers.deploy import _run_deploy
    _run_deploy(record_id, db_url)
