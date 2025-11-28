"""
Demo / operations module for Health and Fitness Club Management System.

This file:
- Connects to PostgreSQL using environment variables (.env)
- Implements core MEMBER operations:
    1) register_member          (Create)
    2) update_member_profile    (Update)
    3) log_health_metric        (Create/Append)
    4) show_member_dashboard    (Read using member_dashboard view)

Later we will add:
- Trainer operations
- Admin operations

Run this file directly for a simple demo:
    python app/demo.py

Or import functions from here in another CLI file.
"""

import os
from datetime import date

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # go up from /app to project root
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", 5432)),
    "dbname": os.getenv("PGDATABASE", "comp3005_proj"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}


def connect():
    """
    Open a new DB connection using DB_CONFIG.
    Uses environment variables from .env (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD).
    """
    # Filter out None values so psycopg2 does not complain
    clean_cfg = {k: v for k, v in DB_CONFIG.items() if v is not None}
    return psycopg2.connect(**clean_cfg)


# --- MEMBER OPERATIONS ------------------------------------------------------


def register_member(conn, email, full_name,
                    date_of_birth=None, gender=None, phone=None):
    """
    Member Registration (Create)

    - Ensures email is unique.
    - Inserts a new row into members with the provided info.
    - Returns the new member id.
    - If the email already exists, prints a message and returns the existing id.
    """
    with conn.cursor() as cur:
        # Check for existing email
        cur.execute("SELECT id FROM members WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            member_id = row[0]
            print(f"[register_member] Member with email {email} already exists (id={member_id})")
            return member_id

        # Insert new member
        cur.execute(
            """
            INSERT INTO members (email, full_name, date_of_birth, gender, phone)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (email, full_name, date_of_birth, gender, phone),
        )
        member_id = cur.fetchone()[0]
        conn.commit()
        print(f"[register_member] Registered member {email} -> id {member_id}")
        return member_id


def update_member_profile(conn, member_id,
                          full_name=None, date_of_birth=None,
                          gender=None, phone=None, email=None):
    """
    Update Profile (Update)

    - Updates editable fields for a member.
    - Only updates the fields that are not None.
    - Returns True if a row was updated, False if member_id does not exist.
    - NOTE: Email must still be unique; if you try to set an email that already
      exists, PostgreSQL will raise an error.
    """
    fields = []
    values = []

    if full_name is not None:
        fields.append("full_name = %s")
        values.append(full_name)
    if date_of_birth is not None:
        fields.append("date_of_birth = %s")
        values.append(date_of_birth)
    if gender is not None:
        fields.append("gender = %s")
        values.append(gender)
    if phone is not None:
        fields.append("phone = %s")
        values.append(phone)
    if email is not None:
        fields.append("email = %s")
        values.append(email)

    if not fields:
        print("[update_member_profile] Nothing to update.")
        return False

    values.append(member_id)

    sql = "UPDATE members SET " + ", ".join(fields) + " WHERE id = %s"
    with conn.cursor() as cur:
        try:
            cur.execute(sql, tuple(values))
            if cur.rowcount == 0:
                print(f"[update_member_profile] No member found with id={member_id}")
                conn.rollback()
                return False
            conn.commit()
            print(f"[update_member_profile] Updated member id={member_id}")
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"[update_member_profile] Failed to update member id={member_id}: {e}")
            return False


def log_health_metric(conn, member_id, metric_type, metric_value):
    """
    Log Health Metric (Create/Append)

    - Inserts a new row into health_metrics.
    - Does NOT overwrite previous entries (historical log).
    """
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO health_metrics (member_id, metric_type, metric_value)
                VALUES (%s, %s, %s)
                """,
                (member_id, metric_type, metric_value),
            )
            conn.commit()
            print(f"[log_health_metric] Logged {metric_type}={metric_value} for member id={member_id}")
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"[log_health_metric] Failed to log metric for member id={member_id}: {e}")
            return False


def show_member_dashboard(conn, member_id):
    """
    Member Dashboard (Read)

    - Reads from the member_dashboard VIEW (defined in DDL.sql).
    - Prints latest metrics, active goals, upcoming sessions, and past class count.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM member_dashboard WHERE member_id = %s",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            print(f"[show_member_dashboard] No dashboard data for member id={member_id}")
            return

        print("------ Member Dashboard ------")
        print(f"Member: {row['full_name']} <{row['email']}>")
        print(f"Latest metrics: {row['latest_metrics']}")
        print(f"Active goals:   {row['active_goals']}")
        print(f"Upcoming sessions: {row['upcoming_sessions']}")
        print(f"Past class count:  {row['past_class_count']}")
        print("------------------------------")


# --- PLACEHOLDERS FOR LATER OPERATIONS --------------------------------------
# We will implement these next, but leave placeholders so the file structure is clear.

def set_trainer_availability(conn, trainer_id, start_ts, end_ts, note=None):
    """TODO: Trainer Set Availability (Create)"""
    raise NotImplementedError


def view_trainer_schedule(conn, trainer_id):
    """TODO: Trainer Schedule View (Read)"""
    raise NotImplementedError


def member_lookup(conn, name_query):
    """TODO: Trainer Member Lookup (Read-only)"""
    raise NotImplementedError


def create_or_update_class_session(conn, class_id, trainer_id, room_id,
                                   start_ts, end_ts, capacity=None, session_id=None):
    """TODO: Admin Create/Update Class Session (Create/Update)"""
    raise NotImplementedError


def register_member_for_class(conn, class_session_id, member_id):
    """TODO: Admin Register Member for Class (capacity + uniqueness)"""
    raise NotImplementedError


def report_equipment_issue(conn, equipment_id, admin_id, issue_description):
    """TODO: Admin Equipment Maintenance (Report)"""
    raise NotImplementedError


def resolve_equipment_issue(conn, maintenance_id):
    """TODO: Admin Equipment Maintenance (Resolve)"""
    raise NotImplementedError


# --- SIMPLE DEMO MAIN -------------------------------------------------------


def main():
    """
    Simple demo flow just to prove the member functions work.
    For the project video, you will probably use a nicer CLI wrapper.
    """
    print("Connecting to DB:", DB_CONFIG["dbname"])
    conn = connect()
    try:
        # 1) Register or get an example member
        member_email = "demo.user@example.com"
        member_full_name = "Demo User"
        member_id = register_member(
            conn,
            email=member_email,
            full_name=member_full_name,
            date_of_birth=date(1998, 1, 1),
            gender="M",
            phone="+1-555-0000",
        )

        # 2) Update profile (show that UPDATE works)
        update_member_profile(
            conn,
            member_id,
            full_name="Demo User Updated",
            phone="+1-555-1111",
        )

        # 3) Log a couple of health metrics
        log_health_metric(conn, member_id, "weight", 78.2)
        log_health_metric(conn, member_id, "heart_rate", 72)

        # 4) Show dashboard (read from the VIEW)
        show_member_dashboard(conn, member_id)

    finally:
        conn.close()


if __name__ == "__main__":
    main()