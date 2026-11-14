
CREATE TABLE IF NOT EXISTS shortage_event (
    shortage_event_id TEXT PRIMARY KEY,

    shortage_id TEXT NOT NULL,

    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'SHORTAGE_DETECTED',
                'SHORTAGE_RESOLVED',
                'SHORTAGE_REOPENED'
            )
        ),

    event_date TEXT NOT NULL,

    resolved_quantity REAL NOT NULL DEFAULT 0
        CHECK (resolved_quantity >= 0),

    source_ref TEXT,

    reason TEXT,

    FOREIGN KEY (shortage_id)
        REFERENCES shortage(shortage_id)
);

CREATE INDEX IF NOT EXISTS idx_shortage_event_shortage
ON shortage_event(shortage_id);

CREATE INDEX IF NOT EXISTS idx_shortage_event_date
ON shortage_event(event_date);
