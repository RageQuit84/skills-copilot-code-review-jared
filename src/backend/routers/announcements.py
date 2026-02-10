"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (within their date range)
    """
    current_time = datetime.utcnow().isoformat() + "Z"
    
    query = {
        "$or": [
            {"start_date": {"$exists": False}},
            {"start_date": {"$lte": current_time}}
        ],
        "expiration_date": {"$gte": current_time}
    }
    
    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """
    Get all announcements (requires authentication) for management purposes
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    announcements = []
    for announcement in announcements_collection.find().sort("created_at", -1):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    teacher_username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new announcement (requires authentication)
    
    - message: The announcement message text
    - expiration_date: ISO 8601 datetime when announcement expires (required)
    - start_date: ISO 8601 datetime when announcement becomes active (optional)
    - teacher_username: Username of authenticated teacher
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO 8601 format")
    
    # Create announcement
    announcement = {
        "message": message,
        "expiration_date": expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if start_date:
        announcement["start_date"] = start_date
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    teacher_username: str = Query(...),
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing announcement (requires authentication)
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO 8601 format")
    
    # Update announcement
    update_data = {
        "message": message,
        "expiration_date": expiration_date,
        "updated_by": teacher_username,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if start_date:
        update_data["start_date"] = start_date
    else:
        # Remove start_date if not provided
        announcements_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$unset": {"start_date": ""}}
        )
    
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    announcement["_id"] = str(announcement["_id"])
    
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """
    Delete an announcement (requires authentication)
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Validate announcement_id before converting to ObjectId to avoid server errors
    if not ObjectId.is_valid(announcement_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid announcement_id format",
        )
    result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
