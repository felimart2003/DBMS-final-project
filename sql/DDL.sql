-- DDL.sql
-- Schema for Health and Fitness Club Management System (PostgreSQL)

-- Enable extension for exclusion constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Members
CREATE TABLE members (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    date_of_birth DATE,
    gender TEXT,
    phone TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Trainers
CREATE TABLE trainers (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    phone TEXT,
    certification TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Admins
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL
);

-- Fitness goals (a member may have multiple goals over time)
CREATE TABLE fitness_goals (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    goal_type TEXT NOT NULL,
    target_value NUMERIC,
    units TEXT,
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE,
    active BOOLEAN DEFAULT TRUE
);

-- Health metrics logged historically (weight, heart rate, etc.)
CREATE TABLE health_metrics (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    metric_type TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Rooms
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    capacity INTEGER NOT NULL DEFAULT 1
);

-- Equipment
CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    room_id INTEGER REFERENCES rooms(id),
    status TEXT DEFAULT 'operational'
);

-- Equipment maintenance logs
CREATE TABLE equipment_maintenance (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    reported_by_admin INTEGER REFERENCES admins(id),
    issue_description TEXT,
    status TEXT NOT NULL DEFAULT 'reported',
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Trainers availability: use tstzrange to allow exclusion constraints for overlaps
CREATE TABLE trainer_availability (
    id SERIAL PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    avail_range TSRANGE NOT NULL,
    note TEXT
);

-- Personal training sessions
CREATE TABLE personal_sessions (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    room_id INTEGER REFERENCES rooms(id),
    session_range TSRANGE NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Classes (types)
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    default_capacity INTEGER DEFAULT 20
);

-- Scheduled class sessions
CREATE TABLE class_sessions (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    trainer_id INTEGER REFERENCES trainers(id),
    room_id INTEGER REFERENCES rooms(id),
    session_range TSRANGE NOT NULL,
    capacity INTEGER,
    status TEXT DEFAULT 'scheduled'
);

-- Registrations for class sessions
CREATE TABLE class_registrations (
    id SERIAL PRIMARY KEY,
    class_session_id INTEGER NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (class_session_id, member_id)
);

-- Billing: invoices, items, payments (simulated)
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    total_amount NUMERIC NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    amount NUMERIC NOT NULL
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL,
    method TEXT,
    paid_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_members_email ON members(email);
CREATE INDEX idx_health_metrics_member_time ON health_metrics(member_id, recorded_at DESC);

-- Exclusion constraints to prevent overlapping bookings for trainer and rooms
-- For personal_sessions: prevent overlapping sessions for same trainer or same room
ALTER TABLE personal_sessions
    ADD CONSTRAINT personal_sessions_no_trainer_overlap EXCLUDE USING GIST (
        trainer_id WITH =,
        session_range WITH &&
    );

ALTER TABLE personal_sessions
    ADD CONSTRAINT personal_sessions_no_room_overlap EXCLUDE USING GIST (
        room_id WITH =,
        session_range WITH &&
    );

-- For class_sessions: prevent overlapping sessions in same room and with same trainer
ALTER TABLE class_sessions
    ADD CONSTRAINT class_sessions_no_room_overlap EXCLUDE USING GIST (
        room_id WITH =,
        session_range WITH &&
    );

ALTER TABLE class_sessions
    ADD CONSTRAINT class_sessions_no_trainer_overlap EXCLUDE USING GIST (
        trainer_id WITH =,
        session_range WITH &&
    );

-- View: member dashboard summary (latest metric list, active goals, upcoming sessions count, past classes count)
CREATE OR REPLACE VIEW member_dashboard AS
SELECT
  m.id AS member_id,
  m.full_name,
  m.email,
  COALESCE(lm.latest_metrics, '[]'::json) AS latest_metrics,
  COALESCE(g.active_goals, '[]'::json) AS active_goals,
  COALESCE(upcoming.upcoming_count, 0) AS upcoming_sessions,
  COALESCE(past.past_class_count, 0) AS past_class_count
FROM members m
LEFT JOIN (
  SELECT hm.member_id,
    json_agg(json_build_object('metric_type', metric_type, 'metric_value', metric_value, 'recorded_at', recorded_at) ORDER BY recorded_at DESC) AS latest_metrics
  FROM health_metrics hm
  GROUP BY hm.member_id
) lm ON lm.member_id = m.id
LEFT JOIN (
  SELECT fg.member_id,
    json_agg(json_build_object('goal_type', goal_type, 'target_value', target_value, 'active', active)) FILTER (WHERE active) AS active_goals
  FROM fitness_goals fg
  GROUP BY fg.member_id
) g ON g.member_id = m.id
LEFT JOIN (
  SELECT ps.member_id, COUNT(*) AS upcoming_count
  FROM personal_sessions ps
  WHERE upper(ps.session_range) > now()
  GROUP BY ps.member_id
) upcoming ON upcoming.member_id = m.id
LEFT JOIN (
  SELECT cr.member_id, COUNT(*) AS past_class_count
  FROM class_registrations cr
  JOIN class_sessions cs ON cs.id = cr.class_session_id
  WHERE upper(cs.session_range) <= now()
  GROUP BY cr.member_id
) past ON past.member_id = m.id;

-- Trigger function: ensure new personal_sessions fall within trainer availability
CREATE OR REPLACE FUNCTION check_personal_session_availability() RETURNS TRIGGER AS $$
BEGIN
  -- Ensure trainer has availability that completely covers the session_range
  IF NOT EXISTS (
    SELECT 1 FROM trainer_availability ta
    WHERE ta.trainer_id = NEW.trainer_id
      AND ta.avail_range @> NEW.session_range
  ) THEN
    RAISE EXCEPTION 'Trainer % is not available for the requested time range', NEW.trainer_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_personal_session_availability
BEFORE INSERT OR UPDATE ON personal_sessions
FOR EACH ROW EXECUTE FUNCTION check_personal_session_availability();
