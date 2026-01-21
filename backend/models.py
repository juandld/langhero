from pydantic import BaseModel
from typing import Optional, List

class Note(BaseModel):
    filename: str
    transcription: Optional[str] = None
    title: Optional[str] = None

class Tag(BaseModel):
    label: str
    color: Optional[str] = None  # hex string like #ff0000

class TagsUpdate(BaseModel):
    tags: List[Tag]


class StoryImportRequest(BaseModel):
    text: Optional[str] = None
    source_url: Optional[str] = None
    setting: Optional[str] = None
    target_language: Optional[str] = None
    max_scenes: Optional[int] = 6
    activate: Optional[bool] = False
    attest_rights: Optional[bool] = False


class AutoImportRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    setting: Optional[str] = None
    target_language: Optional[str] = None
    max_scenes: Optional[int] = 6
    activate: Optional[bool] = False
    attest_rights: Optional[bool] = False
