
-- Migration 003: Add shortage projection traceability.
-- This migration does not insert or modify business records.

CREATE TABLE shortage_projection (
    projection_id TEXT PRIMARY KEY,
    shortage_id TEXT NOT NULL UNIQUE,
    forecast_id TEXT NOT NULL,
    planning_scenario_id TEXT NOT NULL,
    inventory_snapshot_date TEXT NOT NULL,
    projection_date TEXT NOT NULL,
    assumptions TEXT NOT NULL,
    projection_status TEXT NOT NULL DEFAULT 'PROJECTED'
        CHECK (
            projection_status IN (
                'PROJECTED',
                'CONFIRMED',
                'CANCELLED'
            )
        ),

    FOREIGN KEY (shortage_id)
        REFERENCES shortage(shortage_id),

    FOREIGN KEY (forecast_id)
        REFERENCES forecast_demand(forecast_id),

    UNIQUE (
        forecast_id,
        planning_scenario_id,
        inventory_snapshot_date
    )
);

CREATE TABLE shortage_projection_event (
    projection_event_id TEXT PRIMARY KEY,
    projection_id TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'PROJECTION_CREATED',
                'PROJECTION_REVISED',
                'PROJECTION_CONFIRMED',
                'PROJECTION_CANCELLED'
            )
        ),
    event_date TEXT NOT NULL,
    source_ref TEXT,
    reason TEXT NOT NULL,

    FOREIGN KEY (projection_id)
        REFERENCES shortage_projection(projection_id)
);

CREATE INDEX idx_shortage_projection_forecast
ON shortage_projection(forecast_id);

CREATE INDEX idx_shortage_projection_scenario
ON shortage_projection(planning_scenario_id);

CREATE INDEX idx_shortage_projection_event_projection
ON shortage_projection_event(projection_id);
