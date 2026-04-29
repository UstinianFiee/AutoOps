from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, require_operator

router = APIRouter(prefix="/api/tasks", tags=["Ansible任务"])


class TaskRunRequest(BaseModel):
    server_id: int
    task_type: str          # shell / install / playbook / ping
    command: Optional[str] = None       # shell 命令
    packages: Optional[str] = None      # 安装包名，空格分隔
    pkg_manager: Optional[str] = "auto" # apt / yum / auto
    playbook_content: Optional[str] = None  # 自定义 playbook YAML


@router.get("", response_model=List[schemas.TaskOut])
def list_tasks(
    server_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.Task)
    if server_id:
        q = q.filter(models.Task.server_id == server_id)
    return q.order_by(models.Task.id.desc()).limit(100).all()


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/run", response_model=schemas.TaskOut)
def run_task(
    body: TaskRunRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    server = db.query(models.Server).filter(models.Server.id == body.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    task = models.Task(
        server_id=body.server_id,
        task_type=body.task_type,
        target_hosts=server.ip,
        params={
            "command": body.command,
            "packages": body.packages,
            "pkg_manager": body.pkg_manager,
            "playbook_content": body.playbook_content,
        },
        status="pending",
        operator=current_user.username,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.config import settings
    import threading
    threading.Thread(
        target=_run_task_bg,
        args=(task.id, body.server_id, settings.DATABASE_URL),
        daemon=True
    ).start()

    return task


def _build_inventory(server) -> tuple:
    """生成 ansible inventory 内容和临时文件路径"""
    import tempfile, os
    inv = f"[target]\n{server.ip} ansible_port={server.port} ansible_user={server.username} ansible_ssh_extra_args='-o StrictHostKeyChecking=no'"
    if server.auth_type == "password":
        inv += f" ansible_password={server.password}"
    else:
        key_path = f"/tmp/key_{server.id}.pem"
        if server.private_key:
            with open(key_path, "w") as f:
                f.write(server.private_key)
            os.chmod(key_path, 0o600)
        inv += f" ansible_ssh_private_key_file=/tmp/key_{server.id}.pem"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        f.write(inv)
        return f.name


def _run_task_bg(task_id: int, server_id: int, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Task, Server
    import subprocess, tempfile, os

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        server = db.query(Server).filter(Server.id == server_id).first()
        if not task or not server:
            return

        task.status = "running"
        db.commit()

        params = task.params or {}
        inv_path = _build_inventory(server)
        script_path = None  # shell 任务的临时脚本路径

        if task.task_type == "shell":
            # 把命令写到临时 shell 脚本，用 script 模块执行，避免 YAML 特殊字符问题
            cmd = params.get("command", "echo hello")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sh", delete=False, prefix="autoops_cmd_"
            ) as sf:
                sf.write("#!/bin/bash\nset -e\n")
                sf.write(cmd)
                script_path = sf.name
            os.chmod(script_path, 0o755)

            playbook = """---
- hosts: target
  become: yes
  gather_facts: no
  tasks:
    - name: 执行脚本
      script: {script}
      register: result
      ignore_errors: yes
    - name: 输出结果
      debug:
        msg: "{{ result.stdout | default('') }}{{ result.stderr | default('') }}"
""".format(script=script_path)
        elif task.task_type == "install":
            # 安装软件包
            packages = params.get("packages", "")
            pkg_mgr = params.get("pkg_manager", "auto")
            pkg_list = [p.strip() for p in packages.split() if p.strip()]
            pkg_str = "\n".join([f"          - {p}" for p in pkg_list])

            if pkg_mgr == "apt":
                install_task = f"""    - name: apt 安装
      apt:
        name:
{pkg_str}
        state: present
        update_cache: yes
      when: ansible_os_family == "Debian"
"""
            elif pkg_mgr == "yum":
                install_task = f"""    - name: yum 安装
      yum:
        name:
{pkg_str}
        state: present
      when: ansible_os_family == "RedHat"
"""
            else:  # auto
                install_task = f"""    - name: apt 安装
      apt:
        name:
{pkg_str}
        state: present
        update_cache: yes
      when: ansible_os_family == "Debian"
      ignore_errors: yes
    - name: yum 安装
      yum:
        name:
{pkg_str}
        state: present
      when: ansible_os_family == "RedHat"
      ignore_errors: yes
"""
            playbook = f"""---
- hosts: target
  become: yes
  gather_facts: yes
  tasks:
{install_task}
"""
        elif task.task_type == "playbook":
            # 自定义 playbook
            playbook = params.get("playbook_content", "---\n- hosts: target\n  tasks: []")
        else:
            task.status = "failed"
            task.output = f"未知任务类型: {task.task_type}"
            task.finished_at = datetime.utcnow()
            db.commit()
            return

        # 写 playbook 到临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as pf:
            pf.write(playbook)
            pb_path = pf.name

        result = subprocess.run(
            ["ansible-playbook", "-i", inv_path, pb_path],
            capture_output=True, text=True, timeout=600
        )
        task.output = result.stdout + ("\n[STDERR]\n" + result.stderr if result.stderr.strip() else "")
        task.status = "success" if result.returncode == 0 else "failed"
        task.finished_at = datetime.utcnow()
        db.commit()

        # 清理临时文件
        for p in [inv_path, pb_path, script_path]:
            try:
                if p:
                    os.unlink(p)
            except Exception:
                pass

    except Exception as e:
        if task:
            task.status = "failed"
            task.output = str(e)
            task.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
