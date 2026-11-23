CREATE TABLE IF NOT EXISTS patrol_conditions (
    walk_id bigint NOT NULL REFERENCES patrol_walk(id),
    checkpoint text NOT NULL CHECK(checkpoint IN ('outbound','return')),
    measured_at timestamptz NOT NULL,
    visibility_m integer NOT NULL CHECK(visibility_m BETWEEN 1 AND 20000),
    wind_rank integer NOT NULL CHECK(wind_rank BETWEEN 0 AND 12),
    precipitation text NOT NULL CHECK(precipitation IN ('none','light','heavy')),
    PRIMARY KEY(walk_id,checkpoint)
);
CREATE TABLE IF NOT EXISTS weather_disposition (
    walk_id bigint PRIMARY KEY REFERENCES patrol_walk(id),
    usable boolean NOT NULL,
    reason text NOT NULL,
    verified_by text NOT NULL,
    verified_at timestamptz NOT NULL DEFAULT now()
);
