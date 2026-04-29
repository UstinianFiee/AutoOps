from __future__ import annotations
import io
import os
import stat
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models
from app.security import get_current_user, require_operator

router = APIRouter(prefix="/api/sftp", tags=["SFTP文件管理"])


def _get_server(server_id: int, db: Session) -> models.Server:
    server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


def _sftp_client(server: models.Server):
    """建立 SFTP 连接，返回 (ssh_client, sftp_client)"""
    try:
        import paramiko
    except ImportError:
        raise HTTPException(status_code=503, detail="paramiko 未安装")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(
        hostname=server.ip,
        port=server.port,
        username=server.username,
        timeout=15,
    )
    if server.auth_type == "key" and server.private_key:
        kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.private_key))
    else:
        kwargs["password"] = server.password
    try:
        ssh.connect(**kwargs)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SSH 连接失败: {e}")
    sftp = ssh.open_sftp()
    return ssh, sftp


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ── 列目录 ────────────────────────────────────────────────────────────────────

@router.get("/list")
def list_dir(
    server_id: int = Query(...),
    path: str = Query("/"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        entries = []
        for attr in sftp.listdir_attr(path):
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            is_link = stat.S_ISLNK(attr.st_mode) if attr.st_mode else False
            entries.append({
                "name": attr.filename,
                "path": path.rstrip("/") + "/" + attr.filename,
                "is_dir": is_dir,
                "is_link": is_link,
                "size": attr.st_size or 0,
                "size_str": _fmt_size(attr.st_size or 0) if not is_dir else "-",
                "mtime": attr.st_mtime or 0,
                "permissions": oct(stat.S_IMODE(attr.st_mode)) if attr.st_mode else "?",
            })
        # 目录在前，文件在后，各自按名称排序
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"path": path, "entries": entries}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"路径不存在: {path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"无权限访问: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sftp.close()
        ssh.close()


# ── 下载文件 ──────────────────────────────────────────────────────────────────

@router.get("/download")
def download_file(
    server_id: int = Query(...),
    path: str = Query(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        file_stat = sftp.stat(path)
        if stat.S_ISDIR(file_stat.st_mode):
            raise HTTPException(status_code=400, detail="不能下载目录，请先打包")
        buf = io.BytesIO()
        sftp.getfo(path, buf)
        buf.seek(0)
        filename = os.path.basename(path)

        def iter_file():
            try:
                while True:
                    chunk = buf.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                sftp.close()
                ssh.close()

        return StreamingResponse(
            iter_file(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        sftp.close()
        ssh.close()
        raise
    except Exception as e:
        sftp.close()
        ssh.close()
        raise HTTPException(status_code=500, detail=str(e))


# ── 上传文件 ──────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    server_id: int = Query(...),
    path: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        remote_path = path.rstrip("/") + "/" + file.filename
        content = await file.read()
        buf = io.BytesIO(content)
        sftp.putfo(buf, remote_path)
        return {"message": f"上传成功: {remote_path}", "path": remote_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sftp.close()
        ssh.close()


# ── 删除文件/目录 ─────────────────────────────────────────────────────────────

@router.delete("/delete")
def delete_path(
    server_id: int = Query(...),
    path: str = Query(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        file_stat = sftp.stat(path)
        if stat.S_ISDIR(file_stat.st_mode):
            # 递归删除目录
            _, stdout, _ = ssh.exec_command(f"rm -rf '{path}'")
            stdout.channel.recv_exit_status()
        else:
            sftp.remove(path)
        return {"message": f"已删除: {path}"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sftp.close()
        ssh.close()


# ── 重命名/移动 ───────────────────────────────────────────────────────────────

@router.post("/rename")
def rename_path(
    body: dict,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server_id = body.get("server_id")
    old_path = body.get("old_path")
    new_path = body.get("new_path")
    if not all([server_id, old_path, new_path]):
        raise HTTPException(status_code=400, detail="缺少参数")
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        sftp.rename(old_path, new_path)
        return {"message": f"已重命名: {old_path} → {new_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sftp.close()
        ssh.close()


# ── 创建目录 ──────────────────────────────────────────────────────────────────

@router.post("/mkdir")
def make_dir(
    body: dict,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    server_id = body.get("server_id")
    path = body.get("path")
    if not all([server_id, path]):
        raise HTTPException(status_code=400, detail="缺少参数")
    server = _get_server(server_id, db)
    ssh, sftp = _sftp_client(server)
    try:
        sftp.mkdir(path)
        return {"message": f"目录已创建: {path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sftp.close()
        ssh.close()
