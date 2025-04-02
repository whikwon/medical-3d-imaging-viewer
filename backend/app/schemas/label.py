from typing import Any

from pydantic import BaseModel


class CoronaryArtery(BaseModel):
    type: str = "coronaryArtery"
    filename: str
    data: dict[str, Any]
    visible: bool
    color: list[float]
    opacity: float
    id: str
    seriesId: str
