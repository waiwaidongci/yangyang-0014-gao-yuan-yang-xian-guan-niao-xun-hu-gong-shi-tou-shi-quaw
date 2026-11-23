"""Compare start and return conditions against local field comparability rules."""
from pydantic import AwareDatetime, BaseModel, Field
from typing import Literal


class ConditionsInput(BaseModel):
    measured_at: AwareDatetime
    visibility_m: int = Field(ge=1,le=20000)
    wind_rank: int = Field(ge=0,le=12)
    precipitation: Literal["none","light","heavy"]


def classify(rows):
    issues = []
    for item in rows:
        point = "出发" if item["checkpoint"] == "outbound" else "返回"
        if item["visibility_m"] < 100:
            issues.append(point+"能见度低于 100 m")
        if item["wind_rank"] >= 6:
            issues.append(point+"风力达到 6 级")
        if item["precipitation"] == "heavy":
            issues.append(point+"出现强降水")
    return (not issues,"、".join(issues) if issues else "起止条件可用于对照统计")


def qualification(cx, walk_id):
    """Read signed weather gate, leaving pre-extension field records compatible."""
    status = cx.execute("SELECT * FROM weather_disposition WHERE walk_id=%s",(walk_id,)).fetchone()
    if status or cx.execute("SELECT 1 FROM patrol_conditions WHERE walk_id=%s LIMIT 1",(walk_id,)).fetchone():
        return True,status
    return False,None
