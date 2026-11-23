"""Record and lock both weather checkpoints before deciding comparability."""
from datetime import timedelta

from fastapi import HTTPException

from transects import WalkStatus, check_state, walk_for
from weather_rules import classify, qualification


def conditions(cx, walk_id):
    return cx.execute("SELECT * FROM patrol_conditions WHERE walk_id=%s ORDER BY checkpoint",(walk_id,)).fetchall()


def annotate(cx, walk_id, checkpoint, data):
    row = walk_for(cx,walk_id,lock=True)
    if row["status"] not in (WalkStatus.WALKING,WalkStatus.RETURNED):
        raise HTTPException(409,"仅巡护中或返站待复核班可校正天气")
    _, signed = qualification(cx,walk_id)
    if signed:
        raise HTTPException(409,"天气条件已核签")
    end = row["ended_at"] or row["started_at"]+timedelta(hours=8)
    if not row["started_at"] <= data.measured_at <= end:
        raise HTTPException(422,"记录时间不在本班巡护区间")
    return cx.execute(
        """INSERT INTO patrol_conditions VALUES (%s,%s,%s,%s,%s,%s)
           ON CONFLICT(walk_id,checkpoint) DO UPDATE SET measured_at=excluded.measured_at,
           visibility_m=excluded.visibility_m,wind_rank=excluded.wind_rank,precipitation=excluded.precipitation
           RETURNING *""",(walk_id,checkpoint,data.measured_at,data.visibility_m,data.wind_rank,data.precipitation)
    ).fetchone()


def sign_weather(cx, walk_id, reviewer):
    row = walk_for(cx,walk_id,lock=True)
    check_state(row,WalkStatus.RETURNED)
    _, previous = qualification(cx,walk_id)
    if previous:
        return previous
    readings = {item["checkpoint"]:item for item in conditions(cx,walk_id)}
    if set(readings) != {"outbound","return"}:
        raise HTTPException(409,"需补齐起点和终点两次条件记录")
    start, end = readings["outbound"]["measured_at"],readings["return"]["measured_at"]
    if not row["started_at"] <= start <= end <= row["ended_at"]:
        raise HTTPException(409,"起止条件记录时序不正确")
    usable, reason = classify(readings.values())
    return cx.execute("INSERT INTO weather_disposition(walk_id,usable,reason,verified_by) VALUES (%s,%s,%s,%s) RETURNING *",
                      (walk_id,usable,reason,reviewer)).fetchone()
