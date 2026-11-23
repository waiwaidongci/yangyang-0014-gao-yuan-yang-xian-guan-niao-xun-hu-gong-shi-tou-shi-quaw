"""Define an authorized dispatch audience for frozen survey snapshots."""
from enum import StrEnum

from pydantic import BaseModel,ConfigDict,Field


class Audience(StrEnum):
    STATION = "station"
    FIELD_TEAM = "field_team"
    EDUCATION = "education"


class EditionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    series: str = Field(pattern=r"^[a-z][a-z0-9-]{1,39}$")
    snapshot_id: int = Field(gt=0)
    supersedes: int | None = Field(default=None,gt=0)
    reason: str | None = Field(default=None,max_length=300)
    audiences: list[Audience] = Field(min_length=1,max_length=3)
