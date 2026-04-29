from __future__ import annotations
import asyncio, threading
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from app.database import get_db, SessionLocal
from app import models, schemas
from app.security import get_current_user, require_operator
from app.config import settings

router = APIRouter(prefix="/api/deploy", tags=["CI/CD部署"])

# 并发锁：app_id -> threading.Lock
_deploy_locks: Dict[int, threading.Lock] = {}
_locks_mutex = threading.Lock()
_ws_connections: Dict[int, list] = {}


def _get_deploy_lock(app_id: int) -> threading.Lock:
    with _locks_mutex:
        if app_id not in _deploy_locks:
            _deploy_locks[app_id] = threading.Lock()
        return _deploy_locks[app_id]


@router.get("/records", response_model=List[schemas.DeployRecordOut])
def list_records(
    app_id: int = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.DeployRecord)
    if app_id:
        q = q.filter(models.DeployRecord.app_id == app_id)
    return q.order_by(models.DeployRecord.id.desc()).limit(100).all()


@router.get("/preview/{app_id}")
def deploy_preview(
    app_id: int,
    server_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """部署前预览：展示将要执行的操作"""
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    lock = _get_deploy_lock(app_id)
    is_deploying = not lock.acquire(blocking=False)
    if not is_deploying:
        lock.release()

    steps = []
    if app.source_type == "git":
        steps.append(f"1. 从 {app.git_url} 拉取分支 {app.branch}")
    else:
        steps.append("1. 上传本地压缩包到服务器")
    steps.append(f"2. 同步代码到 {server.ip}:{app.deploy_path}/{app.name}")
    steps.append("3. 预检：验证 SSH 连通性 + Docker 环境")
    steps.append("4. docker compose down（停止旧容器）")
    steps.append("5. docker compose pull（拉取最新镜像）")
    steps.append("6. docker compose up -d（启动容器）")
    steps.append("7. 健康检查：验证容器运行状态")

    return {
        "app": {"id": app.id, "name": app.name, "source_type": app.source_type,
                "git_url": app.git_url, "branch": app.branch, "deploy_path": app.deploy_path},
        "server": {"id": server.id, "name": server.name, "ip": server.ip},
        "steps": steps,
        "is_deploying": is_deploying,
        "warning": "该应用正在部署中，请等待完成后再触发" if is_deploying else None,
    }


@router.post("/trigger", response_model=schemas.DeployRecordOut)
def trigger_deploy(
    body: schemas.DeployRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == body.app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    server = db.query(models.Server).filter(models.Server.id == body.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    lock = _get_deploy_lock(body.app_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="该应用正在部署中，请等待完成后再触发")

    record = models.DeployRecord(
        app_id=body.app_id,
        server_id=body.server_id,
        version=body.version or body.branch or app.branch,
        status="pending",
        trigger="manual",
        operator=current_user.username,
    )
    db.add(record)
    app.status = "deploying"
    db.commit()
    db.refresh(record)

    threading.Thread(
        target=_run_deploy,
        args=(record.id, settings.DATABASE_URL, lock),
        daemon=True
    ).start()
    return record


@router.post("/rollback", response_model=schemas.DeployRecordOut)
def rollback(
    body: schemas.RollbackRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    old_record = db.query(models.DeployRecord).filter(
        models.DeployRecord.id == body.record_id,
        models.DeployRecord.status == "success",
    ).first()
    if not old_record:
        raise HTTPException(status_code=404, detail="找不到可回滚的成功记录")

    lock = _get_deploy_lock(old_record.app_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="该应用正在部署中，请等待完成后再触发")

    record = models.DeployRecord(
        app_id=old_record.app_id,
        server_id=old_record.server_id,
        version=old_record.version,
        commit_sha=old_record.commit_sha,
        status="pending",
        trigger="manual",
        operator=current_user.username,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    threading.Thread(
        target=_run_deploy,
        args=(record.id, settings.DATABASE_URL, lock),
        daemon=True
    ).start()
    return record


@router.websocket("/ws/{record_id}")
async def deploy_log_ws(websocket: WebSocket, record_id: int):
    await websocket.accept()
    if record_id not in _ws_connections:
        _ws_connections[record_id] = []
    _ws_connections[record_id].append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            db = SessionLocal()
            record = db.query(models.DeployRecord).filter(
                models.DeployRecord.id == record_id
            ).first()
            db.close()
            if record:
                await websocket.send_json({"status": record.status, "log": record.log or ""})
                if record.status in ("success", "failed"):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if record_id in _ws_connections:
            try:
                _ws_connections[record_id].remove(websocket)
            except ValueError:
                pass


def _run_deploy(record_id: int, db_url: str, lock=None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import DeployRecord, App, Server
    import subprocess, tempfile, os

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    log_lines = []
    inv_path = None
    compose_path = None

    def L(line: str):
        log_lines.append(line)
        record.log = "\n".join(log_lines)
        db.commit()

    try:
        record = db.query(DeployRecord).filter(DeployRecord.id == record_id).first()
        if not record:
            return
        record.status = "running"
        db.commit()

        app = db.query(App).filter(App.id == record.app_id).first()
        server_id = record.server_id or (app.server_id if app else None)
        server = db.query(Server).filter(Server.id == server_id).first() if server_id else None

        if not app:
            record.status = "failed"; record.log = "应用不存在"; db.commit(); return
        if not server:
            record.status = "failed"; record.log = "未绑定服务器"; db.commit(); return

        L(f"[INFO] ===== 开始部署 {app.name} =====")
        L(f"[INFO] 目标服务器: {server.name} ({server.ip})")
        L(f"[INFO] 代码来源: {app.source_type}")
        L(f"[INFO] 部署路径: {app.deploy_path}/{app.name}")

        # 生成 inventory
        inv = (f"[target]\n{server.ip} ansible_port={server.port} "
               f"ansible_user={server.username} "
               f"ansible_ssh_extra_args='-o StrictHostKeyChecking=no'")
        if server.auth_type == "password":
            inv += f" ansible_password={server.password}"
        else:
            key_path = f"/tmp/key_{server.id}.pem"
            if server.private_key:
                with open(key_path, "w") as f:
                    f.write(server.private_key)
                os.chmod(key_path, 0o600)
            inv += f" ansible_ssh_private_key_file={key_path}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write(inv)
            inv_path = f.name

        # 预检：SSH + Docker
        L("[PRECHECK] 验证 SSH 连通性和 Docker 环境...")
        precheck = subprocess.run(
            ["ansible", "-i", inv_path, "target", "-m", "shell",
             "-a", "docker --version 2>&1 && echo PRECHECK_OK"],
            capture_output=True, text=True, timeout=30
        )
        if precheck.returncode != 0 or "PRECHECK_OK" not in precheck.stdout:
            L(f"[PRECHECK FAIL] 预检失败:\n{precheck.stdout}\n{precheck.stderr}")
            record.status = "failed"; record.finished_at = datetime.utcnow()
            app.status = "stopped"; db.commit(); return
        L("[PRECHECK OK] SSH 连通，Docker 可用 ✓")

        # 准备 compose 文件
        if app.compose_content:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False, prefix="compose_"
            ) as f:
                f.write(app.compose_content)
                compose_path = f.name

        # 构建 extra_vars
        extra_vars = (
            f"app_name={app.name} "
            f"deploy_path={app.deploy_path} "
            f"source_type={app.source_type} "
            f"branch={record.version or app.branch}"
        )

        if app.source_type == "git":
            from app.routers.apps import _decrypt_token, _build_git_url_with_token
            git_url = app.git_url or ""
            if app.git_token:
                try:
                    token = _decrypt_token(app.git_token)
                    git_url = _build_git_url_with_token(git_url, token)
                except Exception:
                    pass
            extra_vars += f" git_url={git_url}"
        else:
            extra_vars += f" upload_src={app.upload_path or ''}"

        if compose_path:
            extra_vars += f" compose_src={compose_path}"

        # 执行 playbook
        L("[DEPLOY] 执行 Ansible 部署...")
        result = subprocess.run(
            ["ansible-playbook", "-i", inv_path,
             "/app/ansible/deploy_app.yml",
             "--extra-vars", extra_vars],
            capture_output=True, text=True, timeout=600,
        )
        L(result.stdout)
        if result.stderr.strip():
            L("[STDERR] " + result.stderr)

        if result.returncode != 0:
            L("[ERROR] 部署失败 ✗")
            record.status = "failed"; app.status = "stopped"
            record.finished_at = datetime.utcnow(); db.commit(); return

        # 健康检查
        L("[HEALTH] 检查容器健康状态...")
        health = subprocess.run(
            ["ansible", "-i", inv_path, "target", "-m", "shell",
             "-a", f"cd {app.deploy_path}/{app.name} && docker compose ps 2>&1"],
            capture_output=True, text=True, timeout=60
        )
        L(health.stdout)

        output_lower = health.stdout.lower()
        if "running" in output_lower or "up" in output_lower:
            L("[HEALTH OK] 容器运行正常 ✓")
            record.status = "success"; app.status = "running"
        else:
            L("[HEALTH WARN] 容器未正常启动，收集错误日志...")
            err_log = subprocess.run(
                ["ansible", "-i", inv_path, "target", "-m", "shell",
                 "-a", f"cd {app.deploy_path}/{app.name} && docker compose logs --tail=50 2>&1"],
                capture_output=True, text=True, timeout=30
            )
            L(err_log.stdout)
            record.status = "failed"; app.status = "stopped"

        record.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        if record:
            record.status = "failed"
            record.log = (record.log or "") + f"\n[EXCEPTION] {e}"
            record.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
        if lock:
            try:
                lock.release()
            except RuntimeError:
                pass
        for p in [inv_path, compose_path]:
            if p:
                try:
                    os.unlink(p)
                except Exception:
                    pass
