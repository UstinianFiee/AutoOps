from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app import models
from app.routers import auth, users, servers, apps, deploy, containers, monitor, logs, dashboard, tasks
from app.security import hash_password
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


@app.on_event("startup")
def startup_event():
    """初始化默认管理员账号"""
    db = Session(bind=engine)
    try:
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            admin = models.User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                email="admin@autoops.local",
            )
            db.add(admin)
            db.commit()
            print("[AutoOps] 默认管理员账号已创建: admin / admin123")
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "AutoOps API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
