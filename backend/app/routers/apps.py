from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.security import get_current_user, require_operator

router = APIRouter(prefix="/api/apps", tags=["应用管理"])


@router.get("", response_model=List[schemas.AppOut])
def list_apps(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.App).all()


@router.post("", response_model=schemas.AppOut)
def create_app(
    body: schemas.AppCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    if db.query(models.App).filter(models.App.name == body.name).first():
        raise HTTPException(status_code=400, detail="应用名已存在")
    app = models.App(**body.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/{app_id}", response_model=schemas.AppOut)
def get_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    return app


@router.put("/{app_id}", response_model=schemas.AppOut)
def update_app(
    app_id: int,
    body: schemas.AppUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(app, k, v)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}")
def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    # 先删关联的部署记录，避免外键约束报错
    db.query(models.DeployRecord).filter(models.DeployRecord.app_id == app_id).delete()
    db.delete(app)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{app_id}/start")
def start_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    app.status = "running"
    db.commit()
    return {"message": f"应用 {app.name} 已启动"}


@router.post("/{app_id}/stop")
def stop_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_operator),
):
    app = db.query(models.App).filter(models.App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    app.status = "stopped"
    db.commit()
    return {"message": f"应用 {app.name} 已停止"}
