"""Operate field walks and freeze effort-weighted bird observation pivots."""
from datetime import date, datetime, time
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from core import db, enqueue, require
from pivot import Axis
from transects import LOCAL, WalkStatus, add_encounter, clock_in, clock_out, freeze_snapshot, review_walk, walk_for, load_encounters

router = APIRouter(prefix="/api")
read = Depends(require("operator", "reviewer", "viewer"))
operate = Depends(require("operator"))
review = Depends(require("reviewer"))


class Taxon(StrEnum):
    LARK = "lark"
    WAGTAIL = "wagtail"
    CRANE = "crane"
    DUCK = "duck"
    OTHER = "other"


class PatrolForm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    route_code: str = Field(min_length=1, max_length=32)
    walked_on: date
    crew: str = Field(min_length=2, max_length=60)


class StartForm(BaseModel):
    started_at: AwareDatetime


class BirdForm(BaseModel):
    taxon: Taxon
    observed_at: AwareDatetime
    tally: int = Field(ge=1, le=500)


class ReturnForm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ended_at: AwareDatetime
    completed_route: bool
    zero_declared: bool = False
    early_reason: str | None = Field(default=None, max_length=300)


class PivotForm(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    label: str = Field(min_length=2, max_length=100)
    date_from: date
    date_to: date
    row_axis: Axis
    col_axis: Axis
    taxon: Taxon | None = None

    @model_validator(mode="after")
    def check_axes_and_window(self):
        if not 0 <= (self.date_to - self.date_from).days <= 92:
            raise ValueError("统计日期须按先后选择，跨度最多 92 天")
        if self.row_axis == self.col_axis:
            raise ValueError("行列维度须不同")
        return self


@router.get("/transects")
def routes(user=read):
    with db() as cx:
        return cx.execute("SELECT * FROM transect_route ORDER BY code").fetchall()


@router.get("/patrols")
def patrols(user=read):
    with db() as cx:
        return cx.execute(
            """SELECT w.*, r.label AS route_label, r.cover, r.min_minutes,
               coalesce(sum(e.tally),0) AS observed_count
               FROM patrol_walk w JOIN transect_route r ON r.code=w.route_code
               LEFT JOIN bird_encounter e ON e.walk_id=w.id
               GROUP BY w.id,r.code ORDER BY w.walked_on DESC,w.id DESC"""
        ).fetchall()


@router.post("/patrols", status_code=201)
def book(data: PatrolForm, user=operate):
    with db() as cx:
        if not cx.execute("SELECT 1 FROM transect_route WHERE code=%s", (data.route_code,)).fetchone():
            raise HTTPException(404, "找不到这条样线")
        row = cx.execute(
            """INSERT INTO patrol_walk(route_code,walked_on,crew) VALUES (%s,%s,%s)
               ON CONFLICT DO NOTHING RETURNING *""",
            (data.route_code, data.walked_on, data.crew)
        ).fetchone()
        if row is None:
            raise HTTPException(409, "该小组当天已登记这条样线")
        return row


@router.get("/patrols/{walk_id}")
def trail_log(walk_id: int, user=read):
    with db() as cx:
        return {"walk": walk_for(cx, walk_id), "birds": load_encounters(cx, walk_id)}


@router.post("/patrols/{walk_id}/start")
def start_walk(walk_id: int, data: StartForm, user=operate):
    with db() as cx:
        return clock_in(cx, walk_id, data.started_at)


@router.post("/patrols/{walk_id}/birds", status_code=201)
def record_bird(walk_id: int, data: BirdForm, user=operate):
    with db() as cx:
        return add_encounter(cx, walk_id, data)


@router.post("/patrols/{walk_id}/return")
def return_to_post(walk_id: int, data: ReturnForm, user=operate):
    with db() as cx:
        return clock_out(cx, walk_id, data)


@router.post("/patrols/{walk_id}/review")
def review_patrol(walk_id: int, user=review):
    with db() as cx:
        return review_walk(cx, walk_id, user["email"])


@router.get("/effort")
def archive(user=read):
    with db() as cx:
        return cx.execute(
            """SELECT id,label,date_from,date_to,row_axis,col_axis,taxon,status,frozen_at
               FROM effort_snapshot ORDER BY id DESC"""
        ).fetchall()


@router.get("/effort/{snapshot_id}")
def archived_snapshot(snapshot_id: int, user=read):
    with db() as cx:
        row = cx.execute("SELECT * FROM effort_snapshot WHERE id=%s", (snapshot_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "找不到该透视快照")
        return row


@router.post("/effort", status_code=202)
def prepare_snapshot(data: PivotForm, user=operate):
    with db() as cx:
        item = cx.execute(
            """INSERT INTO effort_snapshot(label,date_from,date_to,row_axis,col_axis,taxon)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
            (data.label, data.date_from, data.date_to, data.row_axis, data.col_axis, data.taxon)
        ).fetchone()
        return {"id": item["id"], "job_id": enqueue(cx, "freeze-bird-effort", {"id": item["id"]})}


def run_job(cx, kind, payload):
    if kind != "freeze-bird-effort":
        raise ValueError(f"Unknown patrol job: {kind}")
    return freeze_snapshot(cx, payload["id"])


def seed(cx):
    for route in [
        ("WX", "苇湾湿地", "wetland", 2.4, 35),
        ("GL", "石岭草甸", "grassland", 3.1, 30),
        ("SR", "背风灌丛", "shrub", 1.2, 25),
    ]:
        cx.execute("INSERT INTO transect_route VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", route)
    for route, day, crew, started, ended, full, early, signed, encounters in [
        ("WX", 16, "白羽组", "08:00", "09:00", True, None, True, [("duck", "08:30", 4)]),
        ("WX", 23, "晨光组", "08:00", "08:45", True, None, True,
         [("crane", "08:12", 6), ("duck", "08:27", 2)]),
        ("WX", 23, "雪线组", "09:25", "09:45", False, "浅滩漫水", True, [("duck", "09:35", 12)]),
        ("GL", 16, "松针组", "07:20", "08:10", True, None, True, [("lark", "07:31", 5)]),
        ("GL", 23, "石岭组", "08:00", "08:40", True, None, True, []),
        ("SR", 23, "流云组", "07:15", "07:45", True, None, False, [("wagtail", "07:29", 3)]),
        ("WX", 24, "晨光组", None, None, None, None, False, []),
    ]:
        stamp = date(2026, 11, day)

        def local_time(value):
            return datetime.combine(stamp, time.fromisoformat(value), LOCAL) if value else None

        inserted = cx.execute(
            """INSERT INTO patrol_walk(route_code,walked_on,crew,status,started_at,ended_at,
                                       completed_route,zero_declared,early_reason)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id""",
            (route, stamp, crew, WalkStatus.RETURNED if ended else WalkStatus.BOOKED,
             local_time(started), local_time(ended), full, bool(full and not encounters), early)
        ).fetchone()
        if not inserted:
            continue
        for taxon, observed, tally in encounters:
            cx.execute("INSERT INTO bird_encounter VALUES (%s,%s,%s,%s)",
                       (inserted["id"], taxon, local_time(observed), tally))
        if signed:
            review_walk(cx, inserted["id"], "reviewer@demo.local")
    saved = cx.execute(
        """INSERT INTO effort_snapshot(label,demo_key,date_from,date_to,row_axis,col_axis)
           VALUES ('十一月巡护双周汇总','bird-demo','2026-11-16','2026-11-23','route','week')
           ON CONFLICT (demo_key) DO NOTHING RETURNING id"""
    ).fetchone()
    if saved:
        freeze_snapshot(cx, saved["id"])
