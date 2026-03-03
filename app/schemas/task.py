from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ========== Task Schemas ==========

class TaskCreate(BaseModel):
    """创建任务请求"""
    language: str = Field(default="auto", description="语言: auto/zh/en")
    speaker_count: Optional[int] = Field(default=None, description="预期说话人数量")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    filename: str
    file_size: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProgressResponse(BaseModel):
    """进度响应"""
    task_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    stage: Optional[str] = None
    stage_description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    estimated_remaining: Optional[int] = None  # seconds

    class Config:
        from_attributes = True


# ========== Transcript Schemas ==========

class TranscriptSegmentResponse(BaseModel):
    """转录片段"""
    speaker: str
    speaker_label: Optional[str] = None
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class TranscriptResponse(BaseModel):
    """转录结果"""
    full_text: Optional[str] = None
    language: Optional[str] = None
    segments: List[TranscriptSegmentResponse] = []


# ========== Minutes Schemas ==========

class KeyPoint(BaseModel):
    """要点"""
    title: str
    content: str


class ActionItem(BaseModel):
    """待办事项"""
    assignee: Optional[str] = None
    task: str
    deadline: Optional[str] = None


class Decision(BaseModel):
    """决策"""
    topic: str
    decision: str


class MinutesResponse(BaseModel):
    """会议纪要"""
    summary: Optional[str] = None
    key_points: List[KeyPoint] = []
    action_items: List[ActionItem] = []
    decisions: List[Decision] = []


class MinutesDetailResponse(BaseModel):
    """会议纪要详情"""
    task_id: str
    transcript: TranscriptResponse
    minutes: MinutesResponse
    created_at: Optional[datetime] = None


# ========== API Response Wrapper ==========

class ApiResponse(BaseModel):
    """统一API响应"""
    code: int = 200
    message: str = "success"
    data: Any = None


# ========== Task List ==========

class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    filename: str
    status: str
    progress: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    items: List[TaskListItem]
    total: int
    page: int
    page_size: int