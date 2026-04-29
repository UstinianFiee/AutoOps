from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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
    """同步拉取（兼容旧调用），推荐使用 GET /images/pull-stream"""
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


@router.get("/images/pull-stream")
def pull_image_stream(
    image: str = Query(...),
    server_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    """SSE 流式拉取镜像，实时返回进度"""
    server = _get_server(server_id, db)

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    if server:
        # 远程：通过 SSH 流式读取 docker pull 输出
        def remote_stream():
            import paramiko, io
            client_ssh = paramiko.SSHClient()
            client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                kwargs = dict(
                    hostname=server.ip, port=server.port,
                    username=server.username, timeout=30
                )
                if server.auth_type == "key" and server.private_key:
                    kwargs["pkey"] = paramiko.RSAKey.from_private_key(
                        io.StringIO(server.private_key)
                    )
                else:
                    kwargs["password"] = server.password
                client_ssh.connect(**kwargs)
                transport = client_ssh.get_transport()
                transport.set_keepalive(30)
                chan = transport.open_session()
                chan.get_pty()
                chan.exec_command(f"docker pull {image}")
                buf = ""
                while True:
                    if chan.recv_ready():
                        chunk = chan.recv(4096).decode("utf-8", errors="replace")
                        buf += chunk
                        lines = buf.split("\n")
                        buf = lines[-1]
                        for line in lines[:-1]:
                            line = line.strip()
                            if line:
                                yield _sse({"type": "progress", "text": line})
                    elif chan.exit_status_ready():
                        break
                if buf.strip():
                    yield _sse({"type": "progress", "text": buf.strip()})
                rc = chan.recv_exit_status()
                if rc == 0:
                    yield _sse({"type": "done", "text": f"镜像 {image} 拉取成功"})
                else:
                    err = chan.recv_stderr(65535).decode("utf-8", errors="replace")
                    yield _sse({"type": "error", "text": err or f"拉取失败，退出码 {rc}"})
            except Exception as e:
                yield _sse({"type": "error", "text": str(e)})
            finally:
                try:
                    client_ssh.close()
                except Exception:
                    pass

        return StreamingResponse(remote_stream(), media_type="text/event-stream")

    else:
        # 本机：使用 Docker SDK 低级 API 流式拉取
        def local_stream():
            if not DOCKER_AVAILABLE:
                yield _sse({"type": "error", "text": "Docker SDK 未安装"})
                return
            try:
                import docker as docker_sdk
                low = docker_sdk.APIClient()
                layers: dict = {}
                for raw in low.pull(image, stream=True, decode=True):
                    status = raw.get("status", "")
                    layer_id = raw.get("id", "")
                    progress = raw.get("progressDetail", {})
                    error = raw.get("error", "")

                    if error:
                        yield _sse({"type": "error", "text": error})
                        return

                    if layer_id:
                        current = progress.get("current", 0)
                        total = progress.get("total", 0)
                        layers[layer_id] = {
                            "status": status,
                            "current": current,
                            "total": total,
                        }
                        total_cur = sum(v["current"] for v in layers.values())
                        total_all = sum(v["total"] for v in layers.values() if v["total"])
                        pct = int(total_cur * 100 / total_all) if total_all else 0
                        yield _sse({
                            "type": "progress",
                            "text": f"[{layer_id[:12]}] {status}",
                            "layer": layer_id,
                            "layerStatus": status,
                            "current": current,
                            "total": total,
                            "percent": pct,
                        })
                    else:
                        if status:
                            yield _sse({"type": "progress", "text": status})

                yield _sse({"type": "done", "text": f"镜像 {image} 拉取成功"})
            except Exception as e:
                yield _sse({"type": "error", "text": str(e)})

        return StreamingResponse(local_stream(), media_type="text/event-stream")
