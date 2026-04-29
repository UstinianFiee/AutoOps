import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from app import models
from app.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/logs", tags=["日志查询"])


@router.get("/query")
async def query_logs(
    query: str = Query(..., description="LogQL 查询语句，如 {job='varlogs'}"),
    start: str = Query(None, description="开始时间 Unix 纳秒或 RFC3339"),
    end: str = Query(None, description="结束时间"),
    limit: int = Query(100, le=1000),
    direction: str = Query("backward", description="forward / backward"),
    _: models.User = Depends(get_current_user),
):
    """查询 Loki 日志"""
    url = f"{settings.LOKI_URL}/loki/api/v1/query_range"
    params = {"query": query, "limit": limit, "direction": direction}
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            # 展平日志行
            lines = []
            for stream in data.get("data", {}).get("result", []):
                labels = stream.get("stream", {})
                for ts, msg in stream.get("values", []):
                    lines.append({"ts": ts, "labels": labels, "msg": msg})
            lines.sort(key=lambda x: x["ts"], reverse=(direction == "backward"))
            return {"lines": lines, "total": len(lines)}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Loki 查询失败: {e}")


@router.get("/labels")
async def get_labels(_: models.User = Depends(get_current_user)):
    """获取 Loki 所有标签"""
    url = f"{settings.LOKI_URL}/loki/api/v1/labels"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Loki 查询失败: {e}")


@router.get("/label/{label}/values")
async def get_label_values(
    label: str,
    _: models.User = Depends(get_current_user),
):
    """获取指定标签的所有值"""
    url = f"{settings.LOKI_URL}/loki/api/v1/label/{label}/values"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Loki 查询失败: {e}")
