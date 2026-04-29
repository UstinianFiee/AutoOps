from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    total_servers = db.query(models.Server).count()
    online_servers = db.query(models.Server).filter(models.Server.status == "online").count()
    total_apps = db.query(models.App).count()
    running_apps = db.query(models.App).filter(models.App.status == "running").count()
    total_deploys = db.query(models.DeployRecord).count()
    success_deploys = db.query(models.DeployRecord).filter(
        models.DeployRecord.status == "success"
    ).count()
    recent_deploys = (
        db.query(models.DeployRecord)
        .order_by(models.DeployRecord.id.desc())
        .limit(10)
        .all()
    )
    return schemas.DashboardStats(
        total_servers=total_servers,
        online_servers=online_servers,
        total_apps=total_apps,
        running_apps=running_apps,
        total_deploys=total_deploys,
        success_deploys=success_deploys,
        recent_deploys=recent_deploys,
    )


@router.get("/tasks", response_model=List[schemas.TaskOut])
def get_recent_tasks(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Task)
        .order_by(models.Task.id.desc())
        .limit(20)
        .all()
    )
