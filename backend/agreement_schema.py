"""Independent tallies, audit observation identities and replacement shift date."""
from datetime import date

from pydantic import BaseModel, ConfigDict,Field,model_validator


class PairObservers(BaseModel):
    observer_one: str = Field(pattern=r"^[A-Z0-9]{2,10}$")
    observer_two: str = Field(pattern=r"^[A-Z0-9]{2,10}$")

    @model_validator(mode="after")
    def independent(self):
        if self.observer_one == self.observer_two:
            raise ValueError("两个独立观察者的代号必须不同")
        return self


class Tally(BaseModel):
    lark: int = Field(ge=0,le=5000)
    wagtail: int = Field(ge=0,le=5000)
    crane: int = Field(ge=0,le=5000)
    duck: int = Field(ge=0,le=5000)
    other: int = Field(ge=0,le=5000)


class RepeatWalk(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    walked_on: date
    crew: str = Field(min_length=2,max_length=60)
