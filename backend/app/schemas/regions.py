from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sido_name: str
    sigungu_name: str
    region_level: str
