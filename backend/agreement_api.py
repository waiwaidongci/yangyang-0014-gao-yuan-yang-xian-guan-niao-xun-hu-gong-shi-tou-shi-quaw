"""Manage paired verification without revealing the other observer's unclosed tally."""
from fastapi import APIRouter,Depends

from agreement_schema import PairObservers,RepeatWalk,Tally
from agreement_service import LIMIT,assess,begin,rebook,submit
from core import db,require

router = APIRouter(prefix="/api/agreement")


@router.get("")
def comparisons(user=Depends(require())):
    with db() as cx:
        tasks = cx.execute("SELECT * FROM observer_comparison ORDER BY id DESC").fetchall()
        posts = cx.execute(
            """SELECT s.comparison_id,s.observer,CASE WHEN c.decision<>'collecting' THEN s.tallies ELSE NULL END AS tallies
               FROM observer_submission s JOIN observer_comparison c ON s.comparison_id=c.id"""
        ).fetchall()
        return {"threshold":LIMIT,"tasks":tasks,"posts":posts}


@router.post("/{walk}/create",status_code=201)
def open_pair(walk: int,data: PairObservers,user=Depends(require("reviewer"))):
    with db() as cx:
        return begin(cx,walk,data)


@router.post("/{id}/observations/{observer}",status_code=201)
def submit_pair(id: int,observer: str,data: Tally,user=Depends(require("operator"))):
    with db() as cx:
        return submit(cx,id,observer,data.model_dump(),user["email"])


@router.post("/{id}/assess")
def evaluate(id: int,user=Depends(require("reviewer"))):
    with db() as cx:
        return assess(cx,id,user["email"])


@router.post("/{id}/repeat")
def repeat(id: int,data: RepeatWalk,user=Depends(require("reviewer"))):
    with db() as cx:
        return rebook(cx,id,data)
