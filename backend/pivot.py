"""Recompute observation rates from summed valid effort, then freeze the matrix."""
from enum import StrEnum
from collections import defaultdict


class Axis(StrEnum):
    ROUTE = "route"
    COVER = "cover"
    WEEK = "week"


def dimension(walk, axis):
    if axis == Axis.ROUTE:
        return walk["route_label"]
    if axis == Axis.COVER:
        return walk["cover"]
    year, week, _ = walk["walked_on"].isocalendar()
    return f"{year}-W{week:02}"


def empty_stats():
    return {"count": 0, "effort_seconds": 0, "walks": 0, "zero_walks": 0}


def add_to(stats, walk):
    stats["count"] += walk["observed_count"]
    stats["effort_seconds"] += int((walk["ended_at"] - walk["started_at"]).total_seconds())
    stats["walks"] += 1
    stats["zero_walks"] += int(walk["zero_declared"])


def with_rate(stats):
    return stats | {"observations_per_hour": (
        stats["count"] * 3600 / stats["effort_seconds"] if stats["effort_seconds"] else None
    )}


def aggregate(walks, row_axis, col_axis):
    stats = defaultdict(empty_stats)
    row_total = defaultdict(empty_stats)
    col_total = defaultdict(empty_stats)
    grand = empty_stats()
    valid = [walk for walk in walks if walk["status"] == "valid"]
    excluded = [walk for walk in walks if walk["status"] == "excluded"]
    for walk in valid:
        row, col = dimension(walk, row_axis), dimension(walk, col_axis)
        add_to(stats[row, col], walk)
        add_to(row_total[row], walk)
        add_to(col_total[col], walk)
        add_to(grand, walk)
    columns = sorted(col_total)
    return {
        "columns": [{"key": col, "total": with_rate(col_total[col])} for col in columns],
        "rows": [
            {"key": row, "cells": [with_rate(stats[row, col]) for col in columns],
             "total": with_rate(row_total[row])}
            for row in sorted(row_total)
        ],
        "grand_total": with_rate(grand),
        "included_walks": [walk["id"] for walk in valid],
        "excluded_walks": [{"id": walk["id"], "reason": walk["review_note"]} for walk in excluded],
        "unreviewed_walks": [walk["id"] for walk in walks if walk["status"] in ("booked", "walking", "returned")],
    }
