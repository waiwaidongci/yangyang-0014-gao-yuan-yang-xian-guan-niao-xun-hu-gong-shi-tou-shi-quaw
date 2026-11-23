"""Check independent observer agreement and rebook the original route when necessary."""
from fastapi import HTTPException
from psycopg.types.json import Jsonb

from transects import WalkStatus,walk_for

LIMIT = .8


def comparison_for(cx,id,lock=False):
    row = cx.execute("SELECT * FROM observer_comparison WHERE id=%s"+(" FOR UPDATE" if lock else ""),(id,)).fetchone()
    if not row:
        raise HTTPException(404,"找不到该复点任务")
    return row


def begin(cx,source,data):
    row = walk_for(cx,source,lock=True)
    if row["status"] not in (WalkStatus.RETURNED,WalkStatus.VALID) or not row["completed_route"]:
        raise HTTPException(409,"复点须引用完整返站的巡护班")
    created = cx.execute(
        """INSERT INTO observer_comparison(source_walk,observer_one,observer_two) VALUES (%s,%s,%s)
           ON CONFLICT DO NOTHING RETURNING *""",(source,data.observer_one,data.observer_two)
    ).fetchone()
    if not created:
        raise HTTPException(409,"该巡护班已有独立复点")
    return created


def submit(cx,id,observer,tallies,operator):
    row = comparison_for(cx,id,lock=True)
    if row["decision"] != "collecting" or observer not in (row["observer_one"],row["observer_two"]):
        raise HTTPException(409,"复点已定结论或该代号不在独立观察配对内")
    submission = cx.execute(
        """INSERT INTO observer_submission VALUES (%s,%s,%s,%s)
           ON CONFLICT DO NOTHING RETURNING comparison_id,observer""",(id,observer,Jsonb(tallies),operator)
    ).fetchone()
    if not submission:
        raise HTTPException(409,"该观察者已经独立交表")
    return submission


def similarity(first,second):
    denominator = sum(max(first[key],second[key]) for key in first)
    return sum(min(value,second[key]) for key,value in first.items())/denominator if denominator else 1.0


def assess(cx,id,reviewer):
    item = comparison_for(cx,id,lock=True)
    if item["decision"] != "collecting":
        raise HTTPException(409,"复点结论已经确认")
    submissions = cx.execute("SELECT tallies FROM observer_submission WHERE comparison_id=%s",(id,)).fetchall()
    if len(submissions) != 2:
        raise HTTPException(409,"等待两个观察者各自交表")
    score = similarity(*(row["tallies"] for row in submissions))
    return cx.execute(
        """UPDATE observer_comparison SET agreement=%s,decision=%s,assessed_by=%s WHERE id=%s RETURNING *""",
        (score,"aligned" if score>=LIMIT else "repeat_required",reviewer,id)
    ).fetchone()


def rebook(cx,id,data):
    task = comparison_for(cx,id,lock=True)
    if task["decision"] != "repeat_required":
        raise HTTPException(409,"当前复点不需再走样线")
    source = walk_for(cx,task["source_walk"])
    if data.walked_on <= source["walked_on"]:
        raise HTTPException(422,"补走日期须晚于原班次")
    walk = cx.execute(
        """INSERT INTO patrol_walk(route_code,walked_on,crew) VALUES (%s,%s,%s)
           ON CONFLICT DO NOTHING RETURNING id""",
        (source["route_code"],data.walked_on,data.crew)
    ).fetchone()
    if not walk:
        raise HTTPException(409,"该组当天同样线已有安排")
    return cx.execute(
        "UPDATE observer_comparison SET decision='repeat_booked',repeat_walk=%s WHERE id=%s RETURNING *",
        (walk["id"],id)
    ).fetchone()
