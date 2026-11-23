CREATE TABLE IF NOT EXISTS observer_comparison (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_walk bigint NOT NULL UNIQUE REFERENCES patrol_walk(id),
    observer_one text NOT NULL,
    observer_two text NOT NULL,
    decision text NOT NULL DEFAULT 'collecting' CHECK(decision IN ('collecting','aligned','repeat_required','repeat_booked')),
    agreement double precision CHECK(agreement BETWEEN 0 AND 1),
    assessed_by text,
    repeat_walk bigint UNIQUE REFERENCES patrol_walk(id),
    CHECK(observer_one <> observer_two),
    CHECK(decision <> 'repeat_booked' OR repeat_walk IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS observer_submission (
    comparison_id bigint NOT NULL REFERENCES observer_comparison(id),
    observer text NOT NULL,
    tallies jsonb NOT NULL,
    posted_by text NOT NULL,
    PRIMARY KEY(comparison_id,observer)
);
