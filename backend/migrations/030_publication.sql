CREATE TABLE IF NOT EXISTS station_edition (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    series text NOT NULL,
    volume integer NOT NULL CHECK(volume > 0),
    snapshot_id bigint NOT NULL REFERENCES effort_snapshot(id),
    supersedes bigint UNIQUE REFERENCES station_edition(id),
    reason text,
    signed_by text NOT NULL,
    stamped_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(series,volume),
    UNIQUE(series,snapshot_id),
    CHECK(volume = 1 OR (supersedes IS NOT NULL AND reason IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS edition_inbox (
    edition_id bigint NOT NULL REFERENCES station_edition(id),
    audience text NOT NULL CHECK(audience IN ('station','field_team','education')),
    received_at timestamptz,
    received_by text,
    PRIMARY KEY(edition_id,audience)
);
