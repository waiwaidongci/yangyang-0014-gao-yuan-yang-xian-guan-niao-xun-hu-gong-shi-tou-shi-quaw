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


def resolve_chains(walks):
    """Count one walk per original: the deepest valid repeat in its rebook chain.

    A failed paired recount alone never removes the original; the booked repeat
    takes over only once it passes review. The counting repeat keeps the root
    walk's walked_on for window and ISO week, but contributes its own tally,
    effort and zero declaration.
    """
    chains = defaultdict(list)
    for walk in walks:
        chains[walk["root_id"]].append(walk)
    counted, makeups, superseded, excluded, unreviewed = [], [], [], [], []
    for chain in chains.values():
        chain.sort(key=lambda walk: walk["depth"])
        root = chain[0]
        incumbent = max((walk for walk in chain if walk["status"] == "valid"),
                        key=lambda walk: walk["depth"], default=None)
        for walk in chain:
            if incumbent and walk["id"] == incumbent["id"]:
                continue
            if walk["status"] == "valid":
                superseded.append({"id": walk["id"], "replaced_by": incumbent["id"]})
            elif walk["status"] == "excluded":
                excluded.append({"id": walk["id"], "reason": walk["review_note"]})
            else:
                unreviewed.append(walk["id"])
        if incumbent:
            counted.append(incumbent if incumbent["id"] == root["id"]
                           else {**incumbent, "walked_on": root["walked_on"]})
            if incumbent["depth"]:
                makeups.append({"id": incumbent["id"], "source_walk": root["id"]})
    counted.sort(key=lambda walk: (walk["walked_on"], walk["id"]))
    return counted, makeups, superseded, excluded, unreviewed


def aggregate(walks, row_axis, col_axis):
    stats = defaultdict(empty_stats)
    row_total = defaultdict(empty_stats)
    col_total = defaultdict(empty_stats)
    grand = empty_stats()
    counted, makeups, superseded, excluded, unreviewed = resolve_chains(walks)
    for walk in counted:
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
        "included_walks": [walk["id"] for walk in counted],
        "makeup_walks": sorted(makeups, key=lambda row: row["id"]),
        "superseded_walks": sorted(superseded, key=lambda row: row["id"]),
        "excluded_walks": sorted(excluded, key=lambda row: row["id"]),
        "unreviewed_walks": sorted(unreviewed),
    }
