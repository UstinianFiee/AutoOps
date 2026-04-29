from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models
from app.security import get_current_user, require_operator

try:
    import docker
    from docker.errors import DockerException, NotFound as DockerNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    DockerNotFound = Exception

router = APIRouter(prefix="/api/containers", tags=["容器管理"])


# ── SSH 远程执行 Docker 命令 ──────────────────────────────────────────────────

def _ssh_exec(server: models.Server, cmd: str) -> tuple[bool, str]:
    """通过 SSH 在远程服务器执行命令，返回 (success, output)"""
    import paramiko, io
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        kwargs = dict(hostname=server.ip, port=server.port, username=server.username, timeout=30)
        if server.auth_type == "key" and server.private_key:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.private_key))
        else:
            kwargs["password"] = server.password
        client.connect(**kwargs)
        _, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        client.close()
        return rc == 0, out + (("\n" + err) if err.strip() else "")
    except Exception as e:
        return False, str(e)


def _get_server(server_id: Optional[int], db: Session) -> Optional[models.Server]:
    if server_id is None:
        return None
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


def _local_docker():
    """获取本机 Docker 客户端"""
    if not DOCKER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Docker SDK 未安装")
    try:
        return docker.from_env()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"本机 Docker 连接失败: {e}")


# ── 容器列表 ──────────────────────────────────────────────────────────────────

@router.get("")
def list_containers(
    all: bool = True,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = _get_server(server_id, db)
    if server:
        # 远程：通过 SSH 执行 docker ps
        ok, out = _ssh_exec(server, 'docker ps -a --format \'{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","state":"{{.State}}","created":"{{.CreatedAt}}"}\' ')
        if not ok:
            raise HTTPException(status_code=502, detail=f"SSH 执行失败: {out}")
        result = []
        for line in out.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                # 统一 status 字段为简短状态
                item["status"] = item.get("state", item.get("status", "unknown")).lower()
                result.append(item)
            except Exception:
                pass
        return result
    else:
        # 本机
        client = _local_docker()
        result = []
        for c in client.containers.list(all=all):
            result.append({
                "id": c.short_id, "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status, "created": c.attrs.get("Created", ""),
            })
        return result


# ── 容器操作 ──────────────────────────────────────────────────────────────────

@router.post("/{container_id}/start")
def start_container(
    container_id: str,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, f"docker start {container_id}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"容器 {container_id} 已启动"}
    client = _local_docker()
    try:
        client.containers.get(container_id).start()
        return {"message": f"容器 {container_id} 已启动"}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="容器不存在")


@router.post("/{container_id}/stop")
def stop_container(
    container_id: str,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, f"docker stop {container_id}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"容器 {container_id} 已停止"}
    client = _local_docker()
    try:
        client.containers.get(container_id).stop()
        return {"message": f"容器 {container_id} 已停止"}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="容器不存在")


@router.post("/{container_id}/restart")
def restart_container(
    container_id: str,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, f"docker restart {container_id}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"容器 {container_id} 已重启"}
    client = _local_docker()
    try:
        client.containers.get(container_id).restart()
        return {"message": f"容器 {container_id} 已重启"}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="容器不存在")


@router.delete("/{container_id}")
def remove_container(
    container_id: str,
    force: bool = False,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    if server:
        flag = "-f" if force else ""
        ok, out = _ssh_exec(server, f"docker rm {flag} {container_id}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"容器 {container_id} 已删除"}
    client = _local_docker()
    try:
        client.containers.get(container_id).remove(force=force)
        return {"message": f"容器 {container_id} 已删除"}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="容器不存在")


@router.get("/{container_id}/logs")
def get_container_logs(
    container_id: str,
    tail: int = 200,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, f"docker logs --tail {tail} --timestamps {container_id} 2>&1")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"logs": out}
    client = _local_docker()
    try:
        c = client.containers.get(container_id)
        logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        return {"logs": logs}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="容器不存在")


# ── 镜像管理 ──────────────────────────────────────────────────────────────────

@router.get("/images/list")
def list_images(
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, 'docker images --format \'{"id":"{{.ID}}","repo":"{{.Repository}}","tag":"{{.Tag}}","size":"{{.Size}}","created":"{{.CreatedAt}}"}\'')
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        result = []
        for line in out.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                repo, tag = item.get("repo", ""), item.get("tag", "")
                result.append({
                    "id": item["id"],
                    "tags": [f"{repo}:{tag}"] if repo and repo != "<none>" else [],
                    "size_mb": item.get("size", ""),
                    "created": item.get("created", ""),
                })
            except Exception:
                pass
        return result
    client = _local_docker()
    result = []
    for img in client.images.list():
        result.append({
            "id": img.short_id, "tags": img.tags,
            "size_mb": round(img.attrs.get("Size", 0) / 1024 / 1024, 2),
            "created": img.attrs.get("Created", ""),
        })
    return result


@router.delete("/images/{image_id}")
def remove_image(
    image_id: str,
    force: bool = False,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    if server:
        flag = "-f" if force else ""
        ok, out = _ssh_exec(server, f"docker rmi {flag} {image_id}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"镜像 {image_id} 已删除"}
    client = _local_docker()
    try:
        client.images.remove(image_id, force=force)
        return {"message": f"镜像 {image_id} 已删除"}
    except DockerNotFound:
        raise HTTPException(status_code=404, detail="镜像不存在")


@router.post("/images/pull")
def pull_image(
    body: dict,
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    image_name = body.get("image")
    if not image_name:
        raise HTTPException(status_code=400, detail="缺少 image 参数")
    server = _get_server(server_id, db)
    if server:
        ok, out = _ssh_exec(server, f"docker pull {image_name}")
        if not ok:
            raise HTTPException(status_code=502, detail=out)
        return {"message": f"镜像 {image_name} 拉取成功"}
    client = _local_docker()
    try:
        client.images.pull(image_name)
        return {"message": f"镜像 {image_name} 拉取成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
