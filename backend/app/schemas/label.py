from typing import Any

from pydantic import BaseModel


class Centerline(BaseModel):
    type: str = "centerline"
    filename: str
    data: dict[str, Any]
    visible: bool
    color: list[float]
    opacity: float
    id: str
    seriesId: str
