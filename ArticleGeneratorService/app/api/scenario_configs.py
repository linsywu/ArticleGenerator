"""
场景路由配置
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import ScenarioConfig
from ..schemas import ScenarioConfigCreate, ScenarioConfigUpdate, ScenarioConfigResponse

router = APIRouter(prefix="/scenario-configs", tags=["场景配置"])


@router.get("", response_model=List[ScenarioConfigResponse])
def list_configs(db: Session = Depends(get_db)):
    return db.query(ScenarioConfig).order_by(ScenarioConfig.sort_order, ScenarioConfig.id).all()


@router.post("", response_model=ScenarioConfigResponse)
def create_config(data: ScenarioConfigCreate, db: Session = Depends(get_db)):
    config = ScenarioConfig(**data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/{config_id}", response_model=ScenarioConfigResponse)
def get_config(config_id: int, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    return c


@router.get("/by-scenario/{scenario}")
def get_config_by_scenario(scenario: str, db: Session = Depends(get_db)):
    """LLMService 网关查询场景配置（含 provider 详情）"""
    c = db.query(ScenarioConfig).filter(
        ScenarioConfig.scenario == scenario,
        ScenarioConfig.enabled == 1
    ).order_by(ScenarioConfig.priority.desc()).first()
    if not c:
        return None
    return {
        "id": c.id,
        "scenario": c.scenario,
        "model": c.model,
        "system_prompt_template": c.system_prompt_template,
        "params": c.params,
        "priority": c.priority,
        "provider": {
            "id": c.provider.id if c.provider else None,
            "name": c.provider.name if c.provider else "",
            "base_url": c.provider.base_url if c.provider else "",
            "api_key": c.provider.api_key if c.provider else "",
        },
    }


@router.put("/{config_id}", response_model=ScenarioConfigResponse)
def update_config(config_id: int, data: ScenarioConfigUpdate, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{config_id}/activate")
def activate_config(config_id: int, db: Session = Depends(get_db)):
    """激活指定配置，同时禁用同场景的其他配置"""
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    # 禁用同场景其他配置
    db.query(ScenarioConfig).filter(
        ScenarioConfig.scenario == c.scenario,
        ScenarioConfig.id != config_id
    ).update({"enabled": 0})
    # 启用当前配置
    c.enabled = 1
    db.commit()
    db.refresh(c)
    return {"message": f"已激活 {c.scenario} 配置 #{c.id}", "config": c}


@router.delete("/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    db.delete(c)
    db.commit()
    return {"message": "删除成功"}
