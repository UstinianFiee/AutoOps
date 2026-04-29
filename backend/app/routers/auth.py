from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.security import verify_password, create_access_token, hash_password, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=schemas.Token)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token({"sub": user.username, "role": user.role})
    return schemas.Token(access_token=token, username=user.username, role=user.role)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    body: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    old_pwd = body.get("old_password", "")
    new_pwd = body.get("new_password", "")
    if not verify_password(old_pwd, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if len(new_pwd) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    current_user.hashed_password = hash_password(new_pwd)
    db.commit()
    return {"message": "密码修改成功"}
