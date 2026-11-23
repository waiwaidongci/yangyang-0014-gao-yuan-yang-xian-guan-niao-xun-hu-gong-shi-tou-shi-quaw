"""Record actual visibility and sign qualification for designated patrols."""
from typing import Literal

from fastapi import APIRouter, Depends

from core import db,require
from transects import walk_for
from weather_rules import ConditionsInput,qualification
from weather_service import annotate,conditions,sign_weather

router = APIRouter(prefix="/api/patrols")


@router.get("/{walk}/weather")
def sheet(walk: int,user=Depends(require())):
    with db() as cx:
        return {"walk":walk_for(cx,walk),"conditions":conditions(cx,walk),
                "assessment":qualification(cx,walk)[1]}


@router.put("/{walk}/weather/{point}")
def save(walk: int,point: Literal["outbound","return"],data: ConditionsInput,user=Depends(require("operator"))):
    with db() as cx:
        return annotate(cx,walk,point,data)


@router.post("/{walk}/weather/sign")
def sign(walk: int,user=Depends(require("reviewer"))):
    with db() as cx:
        return sign_weather(cx,walk,user["email"])
