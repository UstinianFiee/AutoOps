from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, load_only
from sqlalchemy import func, case
from app.database import get_db
from app import models, schemas
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    server_stats = db.query(
        func.count(models.Server.id).label("total"),
        func.sum(case((models.Server.status == "online", 1), else_=0)).label("online"),
    ).first()

    app_stats = db.query(
        func.count(models.App.id).label("total"),
        func.sum(case((models.App.status == "running", 1), else_=0)).label("running"),
    ).first()

    deploy_stats = db.query(
        func.count(models.DeployRecord.id).label("total"),
        func.sum(case((models.DeployRecord.status == "success", 1), else_=0)).label("success"),
    ).first()

    # 最近部署记录：不加载 log 字段（可能很大）
    recent_deploys = (
        db.query(models.DeployRecord)
        .options(load_only(
            models.DeployRecord.id,
            models.DeployRecord.app_id,
            models.DeployRecord.server_id,
            models.DeployRecord.version,
            models.DeployRecord.commit_sha,
            models.DeployRecord.status,
            models.DeployRecord.trigger,
            models.DeployRecord.operator,
            models.DeployRecord.created_at,
            models.DeployRecord.finished_at,
        ))
        .order_by(models.DeployRecord.id.desc())
        .limit(10)
        .all()
    )

    return schemas.DashboardStats(
        total_servers=server_stats.total or 0,
        online_servers=int(server_stats.online or 0),
        total_apps=app_stats.total or 0,
        running_apps=int(app_stats.running or 0),
        total_deploys=deploy_stats.total or 0,
        success_deploys=int(deploy_stats.success or 0),
        recent_deploys=recent_deploys,
    )


@router.get("/tasks", response_model=List[schemas.TaskOut])
def get_recent_tasks(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    # 不加载 output 字段（可能很大），列表只显示摘要
    return (
        db.query(models.Task)
        .options(load_only(
            models.Task.id,
            models.Task.server_id,
            models.Task.task_type,
            models.Task.target_hosts,
            models.Task.status,
            models.Task.operator,
            models.Task.created_at,
            models.Task.finished_at,
        ))
        .order_by(models.Task.id.desc())
        .limit(20)
        .all()
    )
