import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from app.database import get_db, SessionLocal
from app import models, schemas
from app.security import get_current_user, require_operator
from app.config import settings

router = APIRouter(prefix="/api/deploy", tags=["CI/CD部署"])

# 存储 WebSocket 连接：record_id -> [ws]
_ws_connections: Dict[int, list] = {}


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


@router.post("/trigger", response_model=schemas.DeployRecordOut)
def trigger_deploy(
    body: schemas.DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == body.app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    record = models.DeployRecord(
        app_id=body.app_id,
        version=body.version or body.branch or app.branch,
        status="pending",
        trigger="manual",
        operator=current_user.username,
    )
    db.add(record)
    app.status = "deploying"
    db.commit()
    db.refresh(record)

    background_tasks.add_task(_run_deploy, record.id, settings.DATABASE_URL)
    return record


@router.post("/rollback", response_model=schemas.DeployRecordOut)
def rollback(
    body: schemas.RollbackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    old_record = db.query(models.DeployRecord).filter(
        models.DeployRecord.id == body.record_id,
        models.DeployRecord.status == "success",
    ).first()
    if not old_record:
        raise HTTPException(status_code=404, detail="找不到可回滚的成功记录")

    record = models.DeployRecord(
        app_id=old_record.app_id,
        version=old_record.version,
        commit_sha=old_record.commit_sha,
        status="pending",
        trigger="manual",
        operator=current_user.username,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    background_tasks.add_task(_run_deploy, record.id, settings.DATABASE_URL)
    return record


@router.post("/ci-callback")
def ci_callback(payload: dict, db: Session = Depends(get_db)):
    """GitLab CI 回调接口"""
    app_name = payload.get("app_name")
    commit_sha = payload.get("commit_sha", "")
    version = payload.get("version", "")
    status = payload.get("status", "success")

    app = db.query(models.App).filter(models.App.name == app_name).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    record = models.DeployRecord(
        app_id=app.id,
        version=version,
        commit_sha=commit_sha,
        status="pending" if status == "success" else "failed",
        trigger="ci",
        operator="gitlab-ci",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if status == "success":
        from app.config import settings
        import threading
        threading.Thread(
            target=_run_deploy, args=(record.id, settings.DATABASE_URL), daemon=True
        ).start()

    return {"message": "回调已接收", "record_id": record.id}


@router.websocket("/ws/{record_id}")
async def deploy_log_ws(websocket: WebSocket, record_id: int):
    """WebSocket 实时推送部署日志"""
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
                await websocket.send_json({
                    "status": record.status,
                    "log": record.log or "",
                })
                if record.status in ("success", "failed"):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if record_id in _ws_connections:
            _ws_connections[record_id].remove(websocket)


def _run_deploy(record_id: int, db_url: str):
    """后台执行部署任务"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import DeployRecord, App, Server
    import subprocess, tempfile, os

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    log_lines = []

    def append_log(line: str):
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
        if not app:
            record.status = "failed"
            record.log = "应用不存在"
            db.commit()
            return

        server = db.query(Server).filter(Server.id == app.server_id).first()
        if not server:
            record.status = "failed"
            record.log = "未绑定服务器"
            db.commit()
            return

        append_log(f"[INFO] 开始部署应用: {app.name}")
        append_log(f"[INFO] 目标服务器: {server.ip}")
        append_log(f"[INFO] 版本: {record.version}")

        # 写 compose 文件到临时目录
        compose_path = None
        if app.compose_content:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False, prefix="compose_"
            ) as f:
                f.write(app.compose_content)
                compose_path = f.name

        # 生成 inventory
        inv_content = (
            f"[target]\n{server.ip} ansible_port={server.port} "
            f"ansible_user={server.username} "
            f"ansible_ssh_extra_args='-o StrictHostKeyChecking=no'"
        )
        if server.auth_type == "password":
            inv_content += f" ansible_password={server.password}"
        else:
            key_path = f"/tmp/key_{server.id}.pem"
            if server.private_key:
                with open(key_path, "w") as f:
                    f.write(server.private_key)
                os.chmod(key_path, 0o600)
            inv_content += f" ansible_ssh_private_key_file={key_path}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as inv_file:
            inv_file.write(inv_content)
            inv_path = inv_file.name

        extra_vars = (
            f"app_name={app.name} "
            f"deploy_path={app.deploy_path} "
            f"git_url={app.git_url or ''} "
            f"branch={record.version or app.branch}"
        )
        if compose_path:
            extra_vars += f" compose_src={compose_path}"

        result = subprocess.run(
            [
                "ansible-playbook", "-i", inv_path,
                "/app/ansible/deploy_app.yml",
                "--extra-vars", extra_vars,
            ],
            capture_output=True, text=True, timeout=600,
        )
        append_log(result.stdout)
        if result.stderr:
            append_log("[STDERR] " + result.stderr)

        if result.returncode == 0:
            record.status = "success"
            app.status = "running"
            append_log("[INFO] 部署成功 ✓")
        else:
            record.status = "failed"
            app.status = "stopped"
            append_log("[ERROR] 部署失败 ✗")

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
