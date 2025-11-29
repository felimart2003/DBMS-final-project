"""
Interactive CLI for the Health and Fitness Club Management System.

Uses a PostgreSQL database and a .env file for connection settings.
Provides simple command-line menus for member, trainer, and admin actions.

Run with:
    python app/demo.py
"""

import os
from datetime import date, datetime

import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
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
    """Open a new database connection using DB_CONFIG."""
    clean_cfg = {k: v for k, v in DB_CONFIG.items() if v is not None}
    return psycopg2.connect(**clean_cfg)


# ---------------------------------------------------------------------------
# MEMBER OPERATIONS
# ---------------------------------------------------------------------------

def register_member(conn, email, full_name,
                    date_of_birth=None, gender=None, phone=None):
    """
    Create a new member if the email is not already used.

    Returns the member id. If the email already exists, returns the existing id.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM members WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            member_id = row[0]
            print(f"[register_member] Member with email {email} already exists (id={member_id})")
            return member_id

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
    Update basic member fields.

    Only fields that are not None are updated.
    Returns True on success, False if no such member exists.
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
    Insert a new health metric for a member.

    Does not overwrite previous records (historical log).
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
    Print a summary row from the member_dashboard view for a given member.
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


# ---------------------------------------------------------------------------
# TRAINER OPERATIONS
# ---------------------------------------------------------------------------

def list_trainers(conn):
    """Print all trainers with their ids, names, emails, and certifications."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, full_name, email, certification
            FROM trainers
            ORDER BY id;
            """
        )
        rows = cur.fetchall()

        if not rows:
            print("No trainers found.")
            return

        print("=== Trainers ===")
        for row in rows:
            cert = row["certification"] or "(no certification)"
            print(f"{row['id']}: {row['full_name']} <{row['email']}> | {cert}")
        print("===============\n")


def set_trainer_availability(conn, trainer_id, start_ts, end_ts, note=None):
    """
    Insert a new availability range for a trainer.

    Refuses to insert if it overlaps existing availability.
    """
    if isinstance(start_ts, datetime):
        start_ts = start_ts.isoformat()
    if isinstance(end_ts, datetime):
        end_ts = end_ts.isoformat()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM trainer_availability
            WHERE trainer_id = %s
              AND avail_range && tstzrange(%s::timestamptz, %s::timestamptz, '[)')
            """,
            (trainer_id, start_ts, end_ts),
        )
        if cur.fetchone():
            print(
                f"[set_trainer_availability] Overlap detected for trainer_id={trainer_id} "
                f"between {start_ts} and {end_ts}"
            )
            conn.rollback()
            return False

        cur.execute(
            """
            INSERT INTO trainer_availability (trainer_id, avail_range, note)
            VALUES (%s, tstzrange(%s::timestamptz, %s::timestamptz, '[)'), %s)
            RETURNING id
            """,
            (trainer_id, start_ts, end_ts, note),
        )
        avail_id = cur.fetchone()[0]
        conn.commit()
        print(
            f"[set_trainer_availability] Added availability id={avail_id} "
            f"for trainer_id={trainer_id} ({start_ts} -> {end_ts})"
        )
        return True


def view_trainer_schedule(conn, trainer_id, only_upcoming=True):
    """
    Show personal and class sessions for a trainer.

    If only_upcoming is True, only shows sessions that end in the future.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        base_filter_personal = "upper(ps.session_range) > now()" if only_upcoming else "TRUE"
        base_filter_class = "upper(cs.session_range) > now()" if only_upcoming else "TRUE"

        sql = f"""
            SELECT
                'personal' AS kind,
                ps.id AS session_id,
                m.full_name AS member_or_class,
                r.name AS room_name,
                lower(ps.session_range) AS start_time,
                upper(ps.session_range) AS end_time,
                ps.status
            FROM personal_sessions ps
            JOIN members m ON m.id = ps.member_id
            LEFT JOIN rooms r ON r.id = ps.room_id
            WHERE ps.trainer_id = %s
              AND {base_filter_personal}

            UNION ALL

            SELECT
                'class' AS kind,
                cs.id AS session_id,
                c.name AS member_or_class,
                r.name AS room_name,
                lower(cs.session_range) AS start_time,
                upper(cs.session_range) AS end_time,
                cs.status
            FROM class_sessions cs
            JOIN classes c ON c.id = cs.class_id
            LEFT JOIN rooms r ON r.id = cs.room_id
            WHERE cs.trainer_id = %s
              AND {base_filter_class}

            ORDER BY start_time;
        """

        cur.execute(sql, (trainer_id, trainer_id))
        rows = cur.fetchall()

        if not rows:
            print(f"[view_trainer_schedule] No sessions found for trainer_id={trainer_id}")
            return

        print(f"------ Trainer Schedule (trainer_id={trainer_id}) ------")
        for row in rows:
            start = row["start_time"]
            end = row["end_time"]
            kind = row["kind"]
            label = row["member_or_class"]
            room = row["room_name"] or "(no room)"
            status = row["status"]
            print(f"[{kind}] id={row['session_id']} {start} -> {end} | {label} @ {room} | {status}")
        print("--------------------------------------------------------")


def member_lookup(conn, name_query):
    """
    Search members by name (case-insensitive) for a trainer.

    Shows id, basic info, current active goal, and last recorded metric.
    """
    pattern = f"%{name_query}%"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
              m.id,
              m.full_name,
              m.email,
              (
                SELECT fg.goal_type
                FROM fitness_goals fg
                WHERE fg.member_id = m.id
                  AND fg.active = TRUE
                ORDER BY fg.start_date DESC
                LIMIT 1
              ) AS current_goal_type,
              (
                SELECT fg.target_value
                FROM fitness_goals fg
                WHERE fg.member_id = m.id
                  AND fg.active = TRUE
                ORDER BY fg.start_date DESC
                LIMIT 1
              ) AS current_goal_target,
              (
                SELECT hm.metric_type
                FROM health_metrics hm
                WHERE hm.member_id = m.id
                ORDER BY hm.recorded_at DESC
                LIMIT 1
              ) AS last_metric_type,
              (
                SELECT hm.metric_value
                FROM health_metrics hm
                WHERE hm.member_id = m.id
                ORDER BY hm.recorded_at DESC
                LIMIT 1
              ) AS last_metric_value,
              (
                SELECT hm.recorded_at
                FROM health_metrics hm
                WHERE hm.member_id = m.id
                ORDER BY hm.recorded_at DESC
                LIMIT 1
              ) AS last_metric_time
            FROM members m
            WHERE m.full_name ILIKE %s
            ORDER BY m.full_name;
            """,
            (pattern,),
        )

        rows = cur.fetchall()

        if not rows:
            print(f"[member_lookup] No members found matching '{name_query}'")
            return

        print(f"------ Member Lookup for '{name_query}' ------")
        for row in rows:
            print(f"Member id={row['id']} | {row['full_name']} <{row['email']}>")

            if row["current_goal_type"] is not None:
                print(
                    f"  Current goal: {row['current_goal_type']} -> {row['current_goal_target']}"
                )
            else:
                print("  Current goal: (none)")

            if row["last_metric_type"] is not None:
                print(
                    f"  Last metric: {row['last_metric_type']} = {row['last_metric_value']} "
                    f"at {row['last_metric_time']}"
                )
            else:
                print("  Last metric: (none)")

            print()
        print("------------------------------------------------")


# ---------------------------------------------------------------------------
# ADMIN OPERATIONS
# ---------------------------------------------------------------------------

def create_or_update_class_session(conn, class_id, trainer_id, room_id,
                                   start_ts, end_ts, capacity=None, session_id=None):
    """
    Insert a new class session or update an existing one.

    session_id=None  -> insert
    session_id!=None -> update that row
    """
    if isinstance(start_ts, datetime):
        start_ts = start_ts.isoformat()
    if isinstance(end_ts, datetime):
        end_ts = end_ts.isoformat()

    with conn.cursor() as cur:
        try:
            if session_id is None:
                cur.execute(
                    """
                    INSERT INTO class_sessions (class_id, trainer_id, room_id, session_range, capacity)
                    VALUES (%s, %s, %s,
                            tstzrange(%s::timestamptz, %s::timestamptz, '[)'),
                            %s)
                    RETURNING id
                    """,
                    (class_id, trainer_id, room_id, start_ts, end_ts, capacity),
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                print(f"[create_or_update_class_session] Created class_session id={new_id}")
                return new_id
            else:
                cur.execute(
                    """
                    UPDATE class_sessions
                    SET class_id = %s,
                        trainer_id = %s,
                        room_id = %s,
                        session_range = tstzrange(%s::timestamptz, %s::timestamptz, '[)'),
                        capacity = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (class_id, trainer_id, room_id, start_ts, end_ts, capacity, session_id),
                )
                row = cur.fetchone()
                if not row:
                    conn.rollback()
                    print(f"[create_or_update_class_session] No class_session found with id={session_id}")
                    return None
                conn.commit()
                print(f"[create_or_update_class_session] Updated class_session id={session_id}")
                return session_id

        except psycopg2.Error as e:
            conn.rollback()
            print(f"[create_or_update_class_session] Failed to create/update session: {e}")
            return None


def register_member_for_class(conn, class_session_id, member_id):
    """
    Register a member for a class session.

    Checks capacity and the UNIQUE(class_session_id, member_id) constraint.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              cs.id,
              COALESCE(cs.capacity, c.default_capacity) AS max_capacity,
              COUNT(cr.id) AS current_count
            FROM class_sessions cs
            JOIN classes c ON c.id = cs.class_id
            LEFT JOIN class_registrations cr ON cr.class_session_id = cs.id
            WHERE cs.id = %s
            GROUP BY cs.id, max_capacity
            """,
            (class_session_id,),
        )
        row = cur.fetchone()
        if not row:
            print(f"[register_member_for_class] No class_session found with id={class_session_id}")
            return False

        _, max_capacity, current_count = row

        if current_count >= max_capacity:
            print(
                f"[register_member_for_class] Session {class_session_id} is FULL "
                f"({current_count}/{max_capacity})"
            )
            return False

        try:
            cur.execute(
                """
                INSERT INTO class_registrations (class_session_id, member_id)
                VALUES (%s, %s)
                RETURNING id
                """,
                (class_session_id, member_id),
            )
            reg_id = cur.fetchone()[0]
            conn.commit()
            print(
                f"[register_member_for_class] Registered member_id={member_id} "
                f"for class_session_id={class_session_id} (registration id={reg_id})"
            )
            return True

        except errors.UniqueViolation:
            conn.rollback()
            print(
                f"[register_member_for_class] Member {member_id} is already "
                f"registered for session {class_session_id}"
            )
            return False

        except psycopg2.Error as e:
            conn.rollback()
            print(
                f"[register_member_for_class] Failed to register member {member_id} "
                f"for session {class_session_id}: {e}"
            )
            return False


def report_equipment_issue(conn, equipment_id, admin_id, issue_description):
    """
    Create a new maintenance record for a piece of equipment.

    Status starts as 'reported'.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                INSERT INTO equipment_maintenance (equipment_id, reported_by_admin, issue_description)
                VALUES (%s, %s, %s)
                RETURNING id, status, reported_at
                """,
                (equipment_id, admin_id, issue_description),
            )
            row = cur.fetchone()
            conn.commit()
            print(
                f"[report_equipment_issue] Reported issue id={row['id']} on equipment_id={equipment_id} "
                f"status={row['status']} reported_at={row['reported_at']}"
            )
            return row["id"]
        except psycopg2.Error as e:
            conn.rollback()
            print(f"[report_equipment_issue] Failed to report equipment issue: {e}")
            return None


def resolve_equipment_issue(conn, maintenance_id):
    """
    Mark a maintenance record as resolved and set resolved_at=now().

    If the record does not exist or is already resolved, nothing is changed.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                UPDATE equipment_maintenance
                SET status = 'resolved',
                    resolved_at = now()
                WHERE id = %s
                  AND status <> 'resolved'
                RETURNING id, status, resolved_at
                """,
                (maintenance_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                print(
                    f"[resolve_equipment_issue] No open maintenance record found with id={maintenance_id} "
                    f"(it may not exist or is already resolved)."
                )
                return False

            conn.commit()
            print(
                f"[resolve_equipment_issue] Resolved maintenance id={row['id']} at {row['resolved_at']}"
            )
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"[resolve_equipment_issue] Failed to resolve maintenance {maintenance_id}: {e}")
            return False


# ---------------------------------------------------------------------------
# SIMPLE INPUT HELPERS
# ---------------------------------------------------------------------------

def prompt_int(prompt):
    """Read an integer from input. Returns None on blank or invalid."""
    value = input(prompt).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print("Invalid integer.")
        return None


def prompt_float(prompt):
    """Read a float from input. Returns None on blank or invalid."""
    value = input(prompt).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        print("Invalid number.")
        return None


def prompt_date(prompt):
    """Read a date in YYYY-MM-DD format. Returns None on blank or invalid."""
    value = input(prompt + " (YYYY-MM-DD, leave blank for None): ").strip()
    if not value:
        return None
    try:
        year, month, day = map(int, value.split("-"))
        return date(year, month, day)
    except Exception:
        print("Invalid date format.")
        return None


def prompt_timestamp(prompt):
    """
    Read a timestamp in YYYY-MM-DD HH:MM format.

    Keeps asking until the user enters a valid timestamp, or returns None
    if the user just presses Enter.
    """
    while True:
        raw = input(prompt + " (YYYY-MM-DD HH:MM, e.g. 2025-12-05 10:00): ").strip()

        if not raw:
            return None

        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("Invalid date/time (wrong format or impossible date). Please try again.")


# ---------------------------------------------------------------------------
# MENUS
# ---------------------------------------------------------------------------

def member_menu(conn):
    while True:
        print("\n=== Member Menu ===")
        print("1) Register member")
        print("2) Update member profile")
        print("3) Log health metric")
        print("4) Show member dashboard")
        print("0) Back to main menu")
        choice = input("Select option: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            email = input("Email: ").strip()
            full_name = input("Full name: ").strip()
            dob = prompt_date("Date of birth")
            gender = input("Gender (optional): ").strip() or None
            phone = input("Phone (optional): ").strip() or None
            register_member(conn, email, full_name, dob, gender, phone)

        elif choice == "2":
            member_id = prompt_int("Member id: ")
            if not member_id:
                continue
            print("Leave any field blank to keep current value.")
            full_name = input("New full name: ").strip() or None
            dob = prompt_date("New date of birth")
            gender = input("New gender: ").strip() or None
            phone = input("New phone: ").strip() or None
            email = input("New email: ").strip() or None
            update_member_profile(conn, member_id, full_name, dob, gender, phone, email)

        elif choice == "3":
            member_id = prompt_int("Member id: ")
            if not member_id:
                continue
            metric_type = input("Metric type (e.g. weight, heart_rate): ").strip()
            metric_value = prompt_float("Metric value: ")
            if metric_value is None:
                continue
            log_health_metric(conn, member_id, metric_type, metric_value)

        elif choice == "4":
            member_id = prompt_int("Member id: ")
            if not member_id:
                continue
            show_member_dashboard(conn, member_id)

        else:
            print("Invalid choice.")


def trainer_menu(conn):
    while True:
        print("\n=== Trainer Menu ===")
        print("1) Set availability")
        print("2) View trainer schedule")
        print("3) Member lookup")
        print("4) List trainers")
        print("0) Back to main menu")
        choice = input("Select option: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            trainer_id = prompt_int("Trainer id: ")
            if not trainer_id:
                continue
            start_ts = prompt_timestamp("Start time")
            end_ts = prompt_timestamp("End time")
            if not start_ts or not end_ts:
                continue
            note = input("Note (optional): ").strip() or None
            set_trainer_availability(conn, trainer_id, start_ts, end_ts, note)

        elif choice == "2":
            trainer_id = prompt_int("Trainer id: ")
            if not trainer_id:
                continue
            only_upcoming = input("Only upcoming? (y/n, default y): ").strip().lower()
            only_upcoming_flag = (only_upcoming != "n")
            view_trainer_schedule(conn, trainer_id, only_upcoming=only_upcoming_flag)

        elif choice == "3":
            name_query = input("Search member name (partial, case-insensitive): ").strip()
            if not name_query:
                continue
            member_lookup(conn, name_query)

        elif choice == "4":
            list_trainers(conn)

        else:
            print("Invalid choice.")


def admin_menu(conn):
    while True:
        print("\n=== Admin Menu ===")
        print("1) Create class session")
        print("2) Update class session")
        print("3) Register member for class")
        print("4) Report equipment issue")
        print("5) Resolve equipment issue")
        print("0) Back to main menu")
        choice = input("Select option: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            class_id = prompt_int("Class id: ")
            trainer_id = prompt_int("Trainer id: ")
            room_id = prompt_int("Room id: ")
            if not (class_id and trainer_id and room_id):
                continue
            start_ts = prompt_timestamp("Start time")
            end_ts = prompt_timestamp("End time")
            capacity = prompt_int("Capacity (blank to use default from classes): ")
            create_or_update_class_session(
                conn,
                class_id=class_id,
                trainer_id=trainer_id,
                room_id=room_id,
                start_ts=start_ts,
                end_ts=end_ts,
                capacity=capacity,
                session_id=None,
            )

        elif choice == "2":
            session_id = prompt_int("Existing class_session id to update: ")
            if not session_id:
                continue
            class_id = prompt_int("New class id: ")
            trainer_id = prompt_int("New trainer id: ")
            room_id = prompt_int("New room id: ")
            if not (class_id and trainer_id and room_id):
                continue
            start_ts = prompt_timestamp("New start time")
            end_ts = prompt_timestamp("New end time")
            capacity = prompt_int("New capacity (blank to keep NULL): ")
            create_or_update_class_session(
                conn,
                class_id=class_id,
                trainer_id=trainer_id,
                room_id=room_id,
                start_ts=start_ts,
                end_ts=end_ts,
                capacity=capacity,
                session_id=session_id,
            )

        elif choice == "3":
            session_id = prompt_int("Class_session id: ")
            member_id = prompt_int("Member id: ")
            if not (session_id and member_id):
                continue
            register_member_for_class(conn, session_id, member_id)

        elif choice == "4":
            equipment_id = prompt_int("Equipment id: ")
            admin_id = prompt_int("Admin id: ")
            if not (equipment_id and admin_id):
                continue
            desc = input("Issue description: ").strip()
            if not desc:
                print("Description is required.")
                continue
            report_equipment_issue(conn, equipment_id, admin_id, desc)

        elif choice == "5":
            maintenance_id = prompt_int("Maintenance id to resolve: ")
            if not maintenance_id:
                continue
            resolve_equipment_issue(conn, maintenance_id)

        else:
            print("Invalid choice.")


# ---------------------------------------------------------------------------
# MAIN (INTERACTIVE CLI)
# ---------------------------------------------------------------------------

def main():
    print("Connecting to DB:", DB_CONFIG["dbname"])
    conn = connect()
    try:
        while True:
            print("\n=== Main Menu ===")
            print("1) Member operations")
            print("2) Trainer operations")
            print("3) Admin operations")
            print("0) Quit")
            choice = input("Select option: ").strip()

            if choice == "0":
                print("Goodbye.")
                break
            elif choice == "1":
                member_menu(conn)
            elif choice == "2":
                trainer_menu(conn)
            elif choice == "3":
                admin_menu(conn)
            else:
                print("Invalid choice.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
