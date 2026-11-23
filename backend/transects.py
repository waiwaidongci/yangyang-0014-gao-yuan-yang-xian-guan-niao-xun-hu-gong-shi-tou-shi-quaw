"""Field record transition rules and reproducible snapshot materialization."""
from datetime import timedelta, timezone
from enum import StrEnum

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from pivot import aggregate
from weather_rules import qualification

LOCAL = timezone(timedelta(hours=8))


class WalkStatus(StrEnum):
    BOOKED = "booked"
    WALKING = "walking"
    RETURNED = "returned"
    VALID = "valid"
    EXCLUDED = "excluded"


def walk_for(cx, walk_id, lock=False):
    query = "SELECT * FROM patrol_walk WHERE id=%s" + (" FOR UPDATE" if lock else "")
    row = cx.execute(query, (walk_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "找不到该巡护班")
    return row


def check_state(row, expected):
    if row["status"] != expected:
        raise HTTPException(409, "该巡护班当前无法执行此操作")


def load_encounters(cx, walk_id):
    return cx.execute("SELECT * FROM bird_encounter WHERE walk_id=%s ORDER BY observed_at,taxon",
                      (walk_id,)).fetchall()


def clock_in(cx, walk_id, start):
    walk = walk_for(cx, walk_id, lock=True)
    check_state(walk, WalkStatus.BOOKED)
    if start.astimezone(LOCAL).date() != walk["walked_on"]:
        raise HTTPException(422, "开始时间必须落在安排的高原当地日期")
    return cx.execute(
        "UPDATE patrol_walk SET started_at=%s,status=%s WHERE id=%s RETURNING *",
        (start, WalkStatus.WALKING, walk_id)
    ).fetchone()


def add_encounter(cx, walk_id, data):
    walk = walk_for(cx, walk_id, lock=True)
    check_state(walk, WalkStatus.WALKING)
    if not walk["started_at"] <= data.observed_at < walk["started_at"] + timedelta(hours=8):
        raise HTTPException(422, "观测时点须在本班 8 小时巡护窗内")
    row = cx.execute(
        """INSERT INTO bird_encounter VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *""",
        (walk_id, data.taxon, data.observed_at, data.tally)
    ).fetchone()
    if row is None:
        raise HTTPException(409, "同一时点的同种观察已登记")
    return row


def clock_out(cx, walk_id, data):
    walk = walk_for(cx, walk_id, lock=True)
    check_state(walk, WalkStatus.WALKING)
    if not walk["started_at"] < data.ended_at <= walk["started_at"] + timedelta(hours=8):
        raise HTTPException(422, "结束时间须晚于开始，且巡护不超过 8 小时")
    encounters = load_encounters(cx, walk_id)
    if encounters and data.ended_at < encounters[-1]["observed_at"]:
        raise HTTPException(409, "结束时间早于已记录的观测")
    if not data.completed_route and not data.early_reason:
        raise HTTPException(422, "提前折返须填写未到终点原因")
    if data.zero_declared and (not data.completed_route or encounters):
        raise HTTPException(409, "只有完整到终点且没有观测时才可声明有效零")
    if data.completed_route and not encounters and not data.zero_declared:
        raise HTTPException(409, "巡完无观测时请明确声明零记录")
    return cx.execute(
        """UPDATE patrol_walk SET status=%s, ended_at=%s, completed_route=%s, zero_declared=%s,
           early_reason=%s WHERE id=%s RETURNING *""",
        (WalkStatus.RETURNED, data.ended_at, data.completed_route, data.zero_declared,
         None if data.completed_route else data.early_reason, walk_id)
    ).fetchone()


def review_walk(cx, walk_id, reviewer):
    walk = walk_for(cx, walk_id, lock=True)
    check_state(walk, WalkStatus.RETURNED)
    route = cx.execute("SELECT min_minutes FROM transect_route WHERE code=%s",
                       (walk["route_code"],)).fetchone()
    uses_conditions, weather = qualification(cx,walk_id)
    if uses_conditions and not weather:
        raise HTTPException(409, "先核签本班天气与能见度")
    short = (walk["ended_at"] - walk["started_at"]).total_seconds() < route["min_minutes"] * 60
    if not walk["completed_route"]:
        status, note = WalkStatus.EXCLUDED, f"提前折返：{walk['early_reason']}"
    elif short:
        status, note = WalkStatus.EXCLUDED, "虽到终点，但不足该样线最低巡护工时"
    elif weather and not weather["usable"]:
        status, note = WalkStatus.EXCLUDED, weather["reason"]
    else:
        status = WalkStatus.VALID
        note = "完成样线，确认零观测" if walk["zero_declared"] else "完成样线，确认巡护与观测"
    return cx.execute(
        """UPDATE patrol_walk SET status=%s, review_note=%s, checked_by=%s
           WHERE id=%s RETURNING *""",
        (status, note, reviewer, walk_id)
    ).fetchone()


def freeze_snapshot(cx, snapshot_id):
    pending = cx.execute("SELECT * FROM effort_snapshot WHERE id=%s FOR UPDATE", (snapshot_id,)).fetchone()
    if not pending or pending["status"] != "building":
        raise HTTPException(409, "仅可冻结正在编制的透视")
    patrols = cx.execute(
        """SELECT w.*,r.cover,r.label AS route_label,coalesce(sum(e.tally),0) AS observed_count
           FROM patrol_walk w JOIN transect_route r ON w.route_code=r.code
           LEFT JOIN bird_encounter e ON e.walk_id=w.id AND (%s::text IS NULL OR e.taxon=%s)
           WHERE w.walked_on BETWEEN %s AND %s
           GROUP BY w.id,r.code ORDER BY w.walked_on,w.id""",
        (pending["taxon"], pending["taxon"], pending["date_from"], pending["date_to"])
    ).fetchall()
    result = aggregate(patrols, pending["row_axis"], pending["col_axis"])
    cx.execute("UPDATE effort_snapshot SET status='frozen', result=%s, frozen_at=now() WHERE id=%s",
               (Jsonb(result), snapshot_id))
    return result
