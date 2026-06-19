"""
赛道管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Track, SubTrack
from ..schemas import TrackCreate, TrackUpdate, TrackResponse, TrackStatusUpdate, SubTrackCreate, SubTrackResponse

router = APIRouter(prefix="/tracks", tags=["赛道管理"])


@router.get("", response_model=List[TrackResponse])
def list_tracks(db: Session = Depends(get_db)):
    """获取一级赛道列表（含二级赛道）"""
    return db.query(Track).order_by(Track.id.desc()).all()


@router.post("", response_model=TrackResponse)
def create_track(data: TrackCreate, db: Session = Depends(get_db)):
    """新增一级赛道"""
    track = Track(**data.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: int, db: Session = Depends(get_db)):
    """获取赛道详情（含二级赛道列表）"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    return track


@router.put("/{track_id}", response_model=TrackResponse)
def update_track(track_id: int, data: TrackUpdate, db: Session = Depends(get_db)):
    """编辑赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(track, k, v)
    db.commit()
    db.refresh(track)
    return track


@router.patch("/{track_id}/status")
def toggle_track_status(track_id: int, data: TrackStatusUpdate, db: Session = Depends(get_db)):
    """启停赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    track.status = data.status
    db.commit()
    return {"message": "状态已更新"}


@router.delete("/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db)):
    """删除赛道（级联删除二级赛道）"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    db.delete(track)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{track_id}/sub-tracks", response_model=SubTrackResponse)
def create_sub_track(track_id: int, data: SubTrackCreate, db: Session = Depends(get_db)):
    """新增二级赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    sub = SubTrack(track_id=track_id, **data.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.put("/sub-tracks/{sub_track_id}", response_model=SubTrackResponse)
def update_sub_track(sub_track_id: int, data: SubTrackCreate, db: Session = Depends(get_db)):
    """编辑二级赛道"""
    sub = db.query(SubTrack).filter(SubTrack.id == sub_track_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="二级赛道不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/sub-tracks/{sub_track_id}")
def delete_sub_track(sub_track_id: int, db: Session = Depends(get_db)):
    """删除二级赛道"""
    sub = db.query(SubTrack).filter(SubTrack.id == sub_track_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="二级赛道不存在")
    db.delete(sub)
    db.commit()
    return {"message": "删除成功"}
