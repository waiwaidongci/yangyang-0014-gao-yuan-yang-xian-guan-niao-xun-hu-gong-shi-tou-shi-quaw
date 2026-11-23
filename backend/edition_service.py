"""Publish and correct a frozen matrix within its exact original report scope."""
import csv
from io import StringIO

from fastapi import HTTPException

SCOPE = ("date_from","date_to","row_axis","col_axis","taxon")


def snapshot_for(cx,id):
    result = cx.execute("SELECT * FROM effort_snapshot WHERE id=%s",(id,)).fetchone()
    if not result or result["status"] != "frozen":
        raise HTTPException(409,"发布须引用已冻结的透视")
    return result


def publish(cx,data,reviewer):
    cx.execute("SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)", (data.series,))
    snapshot = snapshot_for(cx,data.snapshot_id)
    if not snapshot["result"]["included_walks"] or snapshot["result"]["unreviewed_walks"]:
        raise HTTPException(409,"发布前需有有效工时并复核统计范围内全部班次")
    latest = cx.execute(
        "SELECT * FROM station_edition WHERE series=%s ORDER BY volume DESC LIMIT 1",(data.series,)
    ).fetchone()
    audience = set(data.audiences)
    if latest:
        if latest["id"] != data.supersedes or len(data.reason or "") < 6:
            raise HTTPException(409,"更正须引用当前版次并填写更正依据")
        previous = snapshot_for(cx,latest["snapshot_id"])
        if any(previous[key]!=snapshot[key] for key in SCOPE):
            raise HTTPException(409,"更正不得更换日期、维度或计数鸟种")
        if snapshot["id"] <= previous["id"] or snapshot["result"] == previous["result"]:
            raise HTTPException(409,"需使用有实际统计变化的更新快照")
        mailed = cx.execute("SELECT audience FROM edition_inbox WHERE edition_id=%s",(latest["id"],)).fetchall()
        if not {row["audience"] for row in mailed}.issubset(audience):
            raise HTTPException(409,"更正版须覆盖原版站内收件人")
    elif data.supersedes:
        raise HTTPException(409,"此栏号暂无可更正的发布版")
    volume = latest["volume"]+1 if latest else 1
    new = cx.execute(
        """INSERT INTO station_edition(series,volume,snapshot_id,supersedes,reason,signed_by)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
        (data.series,volume,data.snapshot_id,data.supersedes,data.reason,reviewer)
    ).fetchone()
    for receiver in sorted(audience):
        cx.execute("INSERT INTO edition_inbox(edition_id,audience) VALUES (%s,%s)",(new["id"],receiver))
    return new


def receive(cx,edition,audience,operator):
    row = cx.execute(
        """UPDATE edition_inbox SET received_at=COALESCE(received_at,now()),received_by=COALESCE(received_by,%s)
           WHERE edition_id=%s AND audience=%s RETURNING *""",(operator,edition,audience)
    ).fetchone()
    if not row:
        raise HTTPException(404,"该版次未送此站内收件岗位")
    return row


def export_matrix(snapshot):
    report = snapshot["result"]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([snapshot["row_axis"],snapshot["col_axis"],"count","effort_hours","birds_per_hour","zero_walks"])
    for row in report["rows"]:
        for col,cell in zip(report["columns"],row["cells"],strict=True):
            if cell["effort_seconds"]:
                writer.writerow([row["key"],col["key"],cell["count"],round(cell["effort_seconds"]/3600,4),
                                 round(cell["observations_per_hour"],4),cell["zero_walks"]])
    return output.getvalue()
