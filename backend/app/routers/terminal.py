from __future__ import annotations
import asyncio
import io
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.security import verify_token

router = APIRouter(prefix="/api/terminal", tags=["SSH终端"])

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


async def _run_ssh_session(websocket: WebSocket, ssh_client, label: str):
    """通用 SSH 会话：建立 PTY shell，双向转发数据"""
    ssh_channel = None
    try:
        transport = ssh_client.get_transport()
        transport.set_keepalive(30)
        ssh_channel = transport.open_session()
        ssh_channel.get_pty(term="xterm-256color", width=220, height=50)
        ssh_channel.invoke_shell()

        await websocket.send_text(
            f"\r\n\033[32m[AutoOps] 已连接到 {label}\033[0m\r\n\r\n"
        )

        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        async def read_from_ssh():
            while not stop_event.is_set():
                try:
                    if ssh_channel.recv_ready():
                        data = await loop.run_in_executor(None, ssh_channel.recv, 4096)
                        if not data:
                            stop_event.set()
                            break
                        await websocket.send_bytes(data)
                    elif ssh_channel.exit_status_ready():
                        stop_event.set()
                        break
                    else:
                        await asyncio.sleep(0.02)
                except Exception:
                    stop_event.set()
                    break

        async def write_to_ssh():
            while not stop_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=30)
                    if "text" in message:
                        text = message["text"]
                        if text.startswith("__resize__:"):
                            try:
                                parts = text.split(":")
                                ssh_channel.resize_pty(
                                    width=int(parts[1]), height=int(parts[2])
                                )
                            except Exception:
                                pass
                        else:
                            await loop.run_in_executor(
                                None, ssh_channel.send, text.encode("utf-8")
                            )
                    elif "bytes" in message:
                        await loop.run_in_executor(
                            None, ssh_channel.send, message["bytes"]
                        )
                except WebSocketDisconnect:
                    stop_event.set()
                    break
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    stop_event.set()
                    break

        await asyncio.gather(read_from_ssh(), write_to_ssh())

    finally:
        if ssh_channel:
            try:
                ssh_channel.close()
            except Exception:
                pass


def _check_auth(websocket_accepted, token: str, db: Session):
    """验证 token，返回 user 或 None"""
    return verify_token(token, db)


@router.websocket("/ws")
async def terminal_websocket(
    websocket: WebSocket,
    server_id: int = Query(...),
    token: str = Query(...),
):
    """WebSocket SSH 终端（已保存服务器）"""
    await websocket.accept()

    if not PARAMIKO_AVAILABLE:
        await websocket.send_text("\r\n[ERROR] paramiko 未安装\r\n")
        await websocket.close()
        return

    db: Session = SessionLocal()
    server = None
    try:
        user = verify_token(token, db)
        if not user:
            await websocket.send_text("\r\n[ERROR] 认证失败，请重新登录\r\n")
            await websocket.close(code=4001)
            return
        if user.role not in ("admin", "operator"):
            await websocket.send_text("\r\n[ERROR] 权限不足\r\n")
            await websocket.close(code=4003)
            return
        server = db.query(models.Server).filter(models.Server.id == server_id).first()
        if not server:
            await websocket.send_text("\r\n[ERROR] 服务器不存在\r\n")
            await websocket.close()
            return
        # 把需要的字段取出来，避免 session 关闭后访问
        s_ip = server.ip
        s_port = server.port
        s_username = server.username
        s_auth_type = server.auth_type
        s_password = server.password
        s_private_key = server.private_key
        s_name = server.name
    finally:
        db.close()

    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = dict(hostname=s_ip, port=s_port, username=s_username, timeout=15)
        if s_auth_type == "key" and s_private_key:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(s_private_key))
        else:
            kwargs["password"] = s_password
        ssh_client.connect(**kwargs)
        await _run_ssh_session(websocket, ssh_client, f"{s_name} ({s_ip})")
    except paramiko.AuthenticationException:
        try:
            await websocket.send_text(
                "\r\n\033[31m[ERROR] SSH 认证失败，请检查用户名/密码/密钥\033[0m\r\n"
            )
        except Exception:
            pass
    except Exception as e:
        try:
            await websocket.send_text(f"\r\n\033[31m[ERROR] {e}\033[0m\r\n")
        except Exception:
            pass
    finally:
        if ssh_client:
            try:
                ssh_client.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws-custom")
async def terminal_websocket_custom(
    websocket: WebSocket,
    host: str = Query(...),
    port: int = Query(22),
    username: str = Query("root"),
    auth_type: str = Query("password"),
    password: str = Query(""),
    private_key: str = Query(""),
    token: str = Query(...),
):
    """WebSocket SSH 终端（自定义连接，不依赖已保存服务器）"""
    await websocket.accept()

    if not PARAMIKO_AVAILABLE:
        await websocket.send_text("\r\n[ERROR] paramiko 未安装\r\n")
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        user = verify_token(token, db)
        if not user:
            await websocket.send_text("\r\n[ERROR] 认证失败，请重新登录\r\n")
            await websocket.close(code=4001)
            return
        if user.role not in ("admin", "operator"):
            await websocket.send_text("\r\n[ERROR] 权限不足\r\n")
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = dict(hostname=host, port=port, username=username, timeout=15)
        if auth_type == "key" and private_key:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(private_key))
        else:
            kwargs["password"] = password
        ssh_client.connect(**kwargs)
        await _run_ssh_session(websocket, ssh_client, f"{username}@{host}:{port}")
    except paramiko.AuthenticationException:
        try:
            await websocket.send_text(
                "\r\n\033[31m[ERROR] SSH 认证失败，请检查用户名/密码/密钥\033[0m\r\n"
            )
        except Exception:
            pass
    except Exception as e:
        try:
            await websocket.send_text(f"\r\n\033[31m[ERROR] {e}\033[0m\r\n")
        except Exception:
            pass
    finally:
        if ssh_client:
            try:
                ssh_client.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass
