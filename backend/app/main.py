from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app import models
from app.routers import auth, users, servers, apps, deploy, containers, monitor, logs, dashboard, tasks, terminal, sftp
from sqlalchemy.orm import Session

# 创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoOps API",
    description="轻量自动化运维平台",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(servers.router)
app.include_router(apps.router)
app.include_router(deploy.router)
app.include_router(containers.router)
app.include_router(monitor.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(terminal.router)
app.include_router(sftp.router)


@app.on_event("startup")
def startup_event():
    """初始化：建表、迁移新列、创建默认管理员"""
    from sqlalchemy import text, inspect

    # 自动建表（新表）
    Base.metadata.create_all(bind=engine)

    db = Session(bind=engine)
    try:
        inspector = inspect(engine)

        # ── app 表新列迁移 ────────────────────────────────────────────────────
        app_cols = {c["name"] for c in inspector.get_columns("app")}
        migrations = [
            ("source_type",    "VARCHAR(16) DEFAULT 'git'"),
            ("git_token",      "VARCHAR(512)"),
            ("upload_path",    "VARCHAR(512)"),
            ("webhook_secret", "VARCHAR(128)"),
        ]
        for col_name, col_def in migrations:
            if col_name not in app_cols:
                db.execute(text(f"ALTER TABLE app ADD COLUMN {col_name} {col_def}"))
                print(f"[AutoOps] 迁移: app.{col_name} 已添加")

        # ── deploy_record 表新列迁移 ──────────────────────────────────────────
        dr_cols = {c["name"] for c in inspector.get_columns("deploy_record")}
        if "server_id" not in dr_cols:
            db.execute(text("ALTER TABLE deploy_record ADD COLUMN server_id INT"))
            print("[AutoOps] 迁移: deploy_record.server_id 已添加")

        db.commit()

        # ── 默认管理员 ────────────────────────────────────────────────────────
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            from app.security import hash_password
            admin = models.User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                email="admin@autoops.local",
            )
            db.add(admin)
            db.commit()
            print("[AutoOps] 默认管理员账号已创建: admin / admin123")

    except Exception as e:
        print(f"[AutoOps] startup 异常: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "AutoOps API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
