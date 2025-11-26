"""
Demo script for Health and Fitness Club Management System.

This script connects to PostgreSQL and demonstrates a few operations:
- register member
- log health metric
- show dashboard
- attempt to book a personal training session (validates availability and room/trainer conflicts)

Configure DB connection via environment variables:
  - PGHOST (default: localhost)
  - PGPORT (default: 5432)
  - PGDATABASE (default: fitnessdb)
  - PGUSER
  - PGPASSWORD

Run: python app/demo.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': int(os.getenv('PGPORT', 5432)),
    'dbname': os.getenv('PGDATABASE', 'fitnessdb'),
    'user': os.getenv('PGUSER', None),
    'password': os.getenv('PGPASSWORD', None),
}

def connect():
    conn = psycopg2.connect(**{k:v for k,v in DB_CONFIG.items() if v is not None})
    return conn

def try_register_member(conn, email, full_name):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM members WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            print(f"Member {email} already exists (id={row[0]})")
            return row[0]
        cur.execute("INSERT INTO members (email, full_name) VALUES (%s,%s) RETURNING id", (email, full_name))
        member_id = cur.fetchone()[0]
        conn.commit()
        print(f"Registered member {email} -> id {member_id}")
        return member_id

def log_metric(conn, member_id, metric_type, metric_value):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO health_metrics (member_id, metric_type, metric_value) VALUES (%s,%s,%s)", (member_id, metric_type, metric_value))
        conn.commit()
        print(f"Logged metric {metric_type}={metric_value} for member {member_id}")

def show_dashboard(conn, member_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM member_dashboard WHERE member_id = %s", (member_id,))
        row = cur.fetchone()
        if not row:
            print("No dashboard data for member", member_id)
            return
        print("--- Dashboard ---")
        print(f"Member: {row['full_name']} <{row['email']}>")
        print("Latest metrics:", row['latest_metrics'])
        print("Active goals:", row['active_goals'])
        print(f"Upcoming sessions: {row['upcoming_sessions']}")
        print(f"Past class count: {row['past_class_count']}")

def book_personal_session(conn, member_id, trainer_email, room_name, start_ts, end_ts):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM trainers WHERE email = %s", (trainer_email,))
        t = cur.fetchone()
        if not t:
            raise ValueError('Trainer not found')
        trainer_id = t[0]
        cur.execute("SELECT id FROM rooms WHERE name = %s", (room_name,))
        r = cur.fetchone()
        room_id = r[0] if r else None
        try:
            cur.execute(
                "INSERT INTO personal_sessions (member_id, trainer_id, room_id, session_range) VALUES (%s,%s,%s, tstzrange(%s::timestamptz, %s::timestamptz)) RETURNING id",
                (member_id, trainer_id, room_id, start_ts, end_ts)
            )
            ps_id = cur.fetchone()[0]
            conn.commit()
            print(f"Booked personal session id={ps_id} for member {member_id}")
            return ps_id
        except Exception as e:
            conn.rollback()
            print("Failed to book personal session:", e)
            return None

def main():
    print("Demo script connecting to DB:", DB_CONFIG['dbname'])
    conn = connect()
    try:
        # 1. Register a demo member
        member_email = 'demo.user@example.com'
        member_id = try_register_member(conn, member_email, 'Demo User')

        # 2. Log a health metric
        log_metric(conn, member_id, 'weight', 78.2)

        # 3. Show dashboard
        show_dashboard(conn, member_id)

        # 4. Attempt to book a session tomorrow 09:30-10:30 with Tom
        start_ts = """" + str((os.getenv('DEMO_START') or "")) + """"  # allow overriding via env if desired
        if not start_ts.strip():
            # default: tomorrow 09:30
            start_ts = "'" + ( ("" ) )
        # Build timestamps in SQL-friendly timestamp with timezone using now() + intervals
        # Simpler: compute timestamps relative to now() in SQL during insert
        tomorrow = 'now()::date + INTERVAL ''1 day'''
        start = "(now()::date + INTERVAL '1 day') + INTERVAL '09 hours 30 minutes'"
        end = "(now()::date + INTERVAL '1 day') + INTERVAL '10 hours 30 minutes'"

        print('Attempting to book a personal training session tomorrow 09:30-10:30 with Tom...')
        # For safety, use direct SQL strings for the tstzrange using sub-expressions
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO personal_sessions (member_id, trainer_id, room_id, session_range) VALUES (%s, (SELECT id FROM trainers WHERE email=%s), (SELECT id FROM rooms WHERE name=%s), tstzrange(" + start + ", " + end + ")) RETURNING id",
                    (member_id, 'tom.trainer@example.com', 'Training Room 1')
                )
                ps_id = cur.fetchone()[0]
                conn.commit()
                print('Booked personal session id=', ps_id)
            except Exception as e:
                conn.rollback()
                print('Booking failed:', e)

    finally:
        conn.close()

if __name__ == '__main__':
    main()
