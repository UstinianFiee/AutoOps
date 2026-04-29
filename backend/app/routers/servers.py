from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, require_operator

router = APIRouter(prefix="/api/servers", tags=["服务器管理"])


def _ssh_ping(server: models.Server):
    """同步SSH连通性检测，返回 (success, info)"""
    import paramiko
    import io

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = dict(
            hostname=server.ip,
            port=server.port,
            username=server.username,
            timeout=10,
        )
        if server.auth_type == "key" and server.private_key:
            pkey = paramiko.RSAKey.from_private_key(io.StringIO(server.private_key))
            connect_kwargs["pkey"] = pkey
        else:
            connect_kwargs["password"] = server.password
        client.connect(**connect_kwargs)
        _, stdout, _ = client.exec_command(
            "uname -r && nproc && free -g | awk '/Mem/{print $2}'"
        )
        lines = stdout.read().decode().strip().splitlines()
        os_info = lines[0] if len(lines) > 0 else ""
        cpu = int(lines[1]) if len(lines) > 1 else None
        mem = int(lines[2]) if len(lines) > 2 else None
        client.close()
        return True, os_info, cpu, mem
    except Exception as e:
        return False, str(e), None, None


def _do_ping(server_id: int, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Server

    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        srv = db.query(Server).filter(Server.id == server_id).first()
        if not srv:
            return
        result = _ssh_ping(srv)
        success = result[0]
        srv.status = "online" if success else "offline"
        if success:
            srv.os_info = result[1]
            srv.cpu_cores = result[2]
            srv.memory_gb = result[3]
        db.commit()
    finally:
        db.close()


@router.get("", response_model=List[schemas.ServerOut])
def list_servers(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.Server).all()


@router.post("", response_model=schemas.ServerOut)
def create_server(
    body: schemas.ServerCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    if db.query(models.Server).filter(models.Server.ip == body.ip).first():
        raise HTTPException(status_code=400, detail="该IP已存在")
    server = models.Server(**body.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.get("/{server_id}", response_model=schemas.ServerOut)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.put("/{server_id}", response_model=schemas.ServerOut)
def update_server(
    server_id: int,
    body: schemas.ServerUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(server, k, v)
    db.commit()
    db.refresh(server)
    return server


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    db.delete(server)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{server_id}/ping")
def ping_server(
    server_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    from app.config import settings
    import threading
    threading.Thread(target=_do_ping, args=(server_id, settings.DATABASE_URL), daemon=True).start()
    return {"message": "连通性检测已提交，请稍后刷新"}


@router.post("/{server_id}/init")
def init_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    """使用 Ansible 初始化服务器（安装 Docker 等基础环境）"""
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    task = models.Task(
        server_id=server_id,
        task_type="init",
        target_hosts=server.ip,
        status="pending",
        operator=current_user.username,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.config import settings
    import threading
    threading.Thread(target=_run_ansible_init, args=(task.id, server_id, settings.DATABASE_URL), daemon=True).start()
    return {"message": "初始化任务已提交", "task_id": task.id}


@router.post("/{server_id}/install-exporter")
def install_node_exporter(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    """在被管服务器安装 node_exporter 并加入 Prometheus 监控"""
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    task = models.Task(
        server_id=server_id,
        task_type="install_exporter",
        target_hosts=server.ip,
        status="pending",
        operator=current_user.username,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.config import settings
    import threading
    threading.Thread(
        target=_install_exporter_bg,
        args=(task.id, server_id, settings.DATABASE_URL),
        daemon=True
    ).start()
    return {"message": "安装监控任务已提交", "task_id": task.id}


def _run_ansible_init(task_id: int, server_id: int, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Task, Server
    from datetime import datetime
    import subprocess, tempfile, os

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    key_path = None
    inv_path = None
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        server = db.query(Server).filter(Server.id == server_id).first()
        if not task or not server:
            return
        task.status = "running"
        db.commit()

        # 生成临时 inventory
        inv_content = (
            f"[target]\n{server.ip} "
            f"ansible_port={server.port} "
            f"ansible_user={server.username} "
            f"ansible_ssh_extra_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
        )
        if server.auth_type == "password":
            inv_content += f" ansible_password={server.password}"
        else:
            # 用临时文件存密钥，避免 id 复用冲突
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pem", delete=False, prefix=f"autoops_key_{server_id}_"
            ) as kf:
                kf.write(server.private_key or "")
                key_path = kf.name
            os.chmod(key_path, 0o600)
            inv_content += f" ansible_ssh_private_key_file={key_path}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as inv_file:
            inv_file.write(inv_content)
            inv_path = inv_file.name

        playbook = "/app/ansible/init_server.yml"
        result = subprocess.run(
            ["ansible-playbook", "-i", inv_path, playbook],
            capture_output=True, text=True, timeout=300
        )
        task.output = result.stdout + (("\n[STDERR]\n" + result.stderr) if result.stderr.strip() else "")
        task.status = "success" if result.returncode == 0 else "failed"
        task.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        if task:
            task.status = "failed"
            task.output = str(e)
            task.finished_at = datetime.utcnow()
            db.commit()
    finally:
        for p in [inv_path, key_path]:
            try:
                if p:
                    os.unlink(p)
            except Exception:
                pass
        db.close()


def _install_exporter_bg(task_id: int, server_id: int, db_url: str):
    """后台安装 node_exporter 并更新 Prometheus 配置"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Task, Server
    from datetime import datetime
    import subprocess, tempfile, os

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    key_path = None
    inv_path = None
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        server = db.query(Server).filter(Server.id == server_id).first()
        if not task or not server:
            return
        task.status = "running"
        db.commit()

        # 生成 inventory（同样用临时文件存密钥）
        inv = (
            f"[target]\n{server.ip} "
            f"ansible_port={server.port} "
            f"ansible_user={server.username} "
            f"ansible_ssh_extra_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
        )
        if server.auth_type == "password":
            inv += f" ansible_password={server.password}"
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pem", delete=False, prefix=f"autoops_key_{server_id}_"
            ) as kf:
                kf.write(server.private_key or "")
                key_path = kf.name
            os.chmod(key_path, 0o600)
            inv += f" ansible_ssh_private_key_file={key_path}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write(inv)
            inv_path = f.name

        pb_path = "/app/ansible/install_node_exporter.yml"
        result = subprocess.run(
            ["ansible-playbook", "-i", inv_path, pb_path],
            capture_output=True, text=True, timeout=300
        )
        output = result.stdout + (("\n[STDERR]\n" + result.stderr) if result.stderr.strip() else "")

        if result.returncode == 0:
            _update_prometheus_config(server.ip, server.name)
            output += f"\n\n[INFO] 已将 {server.ip}:9100 加入 Prometheus 监控"
            task.status = "success"
        else:
            task.status = "failed"

        task.output = output
        task.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        if task:
            task.status = "failed"
            task.output = str(e)
            task.finished_at = datetime.utcnow()
            db.commit()
    finally:
        for p in [inv_path, key_path]:
            try:
                if p:
                    os.unlink(p)
            except Exception:
                pass
        db.close()


def _update_prometheus_config(ip: str, name: str = ""):
    """动态将服务器加入 Prometheus 采集配置并热重载（追加方式，保留原有注释）"""
    import requests, re

    prom_config_path = "/etc/autoops/prometheus.yml"
    target = f"{ip}:9100"

    try:
        with open(prom_config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已存在
        if target in content:
            print(f"[INFO] {target} 已在 Prometheus 配置中，跳过")
        else:
            # 在 node job 的 static_configs 末尾追加新 target
            # 找到 job_name: 'node' 块，在其最后一个 targets 行后追加
            label = name or ip
            new_entry = (
                f"      - targets: ['{target}']\n"
                f"        labels:\n"
                f"          alias: '{label}'\n"
            )
            # 在注释行（# 远程受管服务器）后面插入，或在 node job 末尾追加
            if "# 远程受管服务器" in content:
                # 找到注释行，在其后插入
                content = content.replace(
                    "# 远程受管服务器",
                    f"# 远程受管服务器\n{new_entry}",
                    1
                )
            else:
                # 在 cadvisor job 前插入
                content = content.replace(
                    "  - job_name: 'cadvisor'",
                    f"{new_entry}  - job_name: 'cadvisor'",
                    1
                )

            with open(prom_config_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[INFO] 已追加采集目标: {target}")

        # 热重载 Prometheus
        from app.config import settings
        resp = requests.post(f"{settings.PROMETHEUS_URL}/-/reload", timeout=5)
        if resp.status_code == 200:
            print(f"[INFO] Prometheus 热重载成功")
        else:
            print(f"[WARN] Prometheus 热重载返回: {resp.status_code}")

    except Exception as e:
        print(f"[WARN] 更新 Prometheus 配置失败: {e}")
