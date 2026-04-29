import httpx
from fastapi import APIRouter, Depends, HTTPException
from app import models
from app.security import get_current_user, require_operator
from app.config import settings

router = APIRouter(prefix="/api/monitor", tags=["监控告警"])


@router.get("/metrics")
async def query_metrics(
    query: str,
    _: models.User = Depends(get_current_user),
):
    """即时查询 Prometheus 指标"""
    url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params={"query": query})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Prometheus 查询失败: {e}")


@router.get("/metrics/range")
async def query_metrics_range(
    query: str,
    start: str,
    end: str,
    step: str = "60s",
    _: models.User = Depends(get_current_user),
):
    """范围查询 Prometheus 指标"""
    url = f"{settings.PROMETHEUS_URL}/api/v1/query_range"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params={
                "query": query, "start": start, "end": end, "step": step
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Prometheus 查询失败: {e}")


@router.get("/alerts")
async def get_alerts(_: models.User = Depends(get_current_user)):
    """获取 Alertmanager 当前告警"""
    alertmanager_url = settings.PROMETHEUS_URL.replace("prometheus:9090", "alertmanager:9093").replace("9090", "9093")
    url = f"{alertmanager_url}/api/v2/alerts"
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            # Alertmanager 不可用时返回空列表，不报错
            return []


@router.get("/overview")
async def get_overview(
    instance: str = None,
    _: models.User = Depends(get_current_user)
):
    """获取主机概览指标（CPU、内存、磁盘），支持指定 instance"""
    # instance 格式如 "192.168.1.1:9100"
    inst_filter = f',instance="{instance}"' if instance else ''
    queries = {
        "cpu_usage": f'100 - (avg(irate(node_cpu_seconds_total{{mode="idle"{inst_filter}}}[5m])) * 100)',
        "mem_usage": f'(1 - (node_memory_MemAvailable_bytes{{{inst_filter.lstrip(",")}}} / node_memory_MemTotal_bytes{{{inst_filter.lstrip(",")}}})) * 100',
        "disk_usage": f'(1 - (node_filesystem_avail_bytes{{mountpoint="/",fstype!="tmpfs"{inst_filter}}} / node_filesystem_size_bytes{{mountpoint="/",fstype!="tmpfs"{inst_filter}}})) * 100',
        "load1": f'node_load1{{{inst_filter.lstrip(",")}}}',
    }
    result = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for key, q in queries.items():
            try:
                resp = await client.get(
                    f"{settings.PROMETHEUS_URL}/api/v1/query",
                    params={"query": q}
                )
                data = resp.json()
                results = data.get("data", {}).get("result", [])
                result[key] = float(results[0]["value"][1]) if results else None
            except Exception:
                result[key] = None
    return result
