CREATE TABLE IF NOT EXISTS transect_route (
    code text PRIMARY KEY,
    label text NOT NULL,
    cover text NOT NULL CHECK (cover IN ('grassland','wetland','shrub')),
    km double precision NOT NULL CHECK (km > 0),
    min_minutes integer NOT NULL CHECK (min_minutes BETWEEN 5 AND 240)
);
CREATE TABLE IF NOT EXISTS patrol_walk (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_code text NOT NULL REFERENCES transect_route(code),
    walked_on date NOT NULL,
    crew text NOT NULL CHECK (char_length(crew) BETWEEN 2 AND 60),
    status text NOT NULL DEFAULT 'booked' CHECK (status IN
        ('booked','walking','returned','valid','excluded')),
    started_at timestamptz,
    ended_at timestamptz,
    completed_route boolean,
    zero_declared boolean NOT NULL DEFAULT false,
    early_reason text,
    review_note text,
    checked_by text,
    UNIQUE (route_code, walked_on, crew),
    CHECK (ended_at IS NULL OR ended_at > started_at),
    CHECK (status = 'booked' OR started_at IS NOT NULL),
    CHECK (status NOT IN ('returned','valid','excluded') OR (ended_at IS NOT NULL AND completed_route IS NOT NULL)),
    CHECK (status NOT IN ('valid','excluded') OR checked_by IS NOT NULL),
    CHECK (NOT zero_declared OR completed_route)
);
CREATE TABLE IF NOT EXISTS bird_encounter (
    walk_id bigint NOT NULL REFERENCES patrol_walk(id),
    taxon text NOT NULL CHECK (taxon IN ('lark','wagtail','crane','duck','other')),
    observed_at timestamptz NOT NULL,
    tally integer NOT NULL CHECK (tally BETWEEN 1 AND 500),
    PRIMARY KEY (walk_id,taxon,observed_at)
);
CREATE TABLE IF NOT EXISTS effort_snapshot (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    label text NOT NULL CHECK (char_length(label) BETWEEN 2 AND 100),
    demo_key text UNIQUE,
    date_from date NOT NULL,
    date_to date NOT NULL,
    row_axis text NOT NULL CHECK (row_axis IN ('route','cover','week')),
    col_axis text NOT NULL CHECK (col_axis IN ('route','cover','week')),
    taxon text CHECK (taxon IN ('lark','wagtail','crane','duck','other')),
    status text NOT NULL DEFAULT 'building' CHECK (status IN ('building','frozen')),
    result jsonb,
    frozen_at timestamptz,
    CHECK (date_from <= date_to AND date_to - date_from <= 92),
    CHECK (row_axis <> col_axis),
    CHECK (status <> 'frozen' OR (result IS NOT NULL AND frozen_at IS NOT NULL))
);
