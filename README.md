# Health & Fitness Club Management System

This repository contains a PostgreSQL-based schema and a small Python demo for a Health and Fitness Club Management System. The project demonstrates database design (DDL), sample data (DML), and example operations for Members, Trainers, and Admins.

Contents
- `sql/DDL.sql` : PostgreSQL schema (tables, constraints, view, trigger, indexes)
- `sql/DML.sql` : Sample data to populate the database
- `app/demo.py` : Python demo script (uses `psycopg2`) to demonstrate a few operations
- `docs/ERD.md` : ERD placeholder and instructions (please add `ERD.pdf` before submission)

Quick Setup (Windows PowerShell)

1. Create a PostgreSQL database (example uses `fitnessdb`):

```powershell
# create DB (run in psql or using pgAdmin)
createdb -U postgres fitnessdb
```

2. Run DDL to create schema, then DML to insert sample data:

```powershell
psql -U postgres -d fitnessdb -f sql/DDL.sql
psql -U postgres -d fitnessdb -f sql/DML.sql
```

3. Install Python dependencies and run demo:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install psycopg2-binary
# Set DB env vars if different from defaults
$env:PGDATABASE = 'fitnessdb'
$env:PGUSER = 'postgres'
$env:PGPASSWORD = 'yourpassword'
python app/demo.py
```

Notes
- The demo script is minimal and intended to show how to run and validate a few operations. It demonstrates member registration, health metric logging, dashboard view, and an attempt to book a personal training session (which exercises availability checks and exclusion constraints).
- The schema uses `tstzrange` types and PostgreSQL exclusion constraints to prevent overlapping bookings for trainers and rooms. It also includes a `member_dashboard` view and a trigger that ensures personal sessions fall within trainer availability.

Next steps / what to include in final submission
- Add a complete ERD PDF at `docs/ERD.pdf` showing entities, relationships, keys, and cardinality.
- Optionally implement an application UI or CLI to cover all required functions for Members, Trainers, and Admins.
- Record a demo video (unlisted YouTube) showing: ERD, mapping, schema files or ORM code, and functionality demo (success and at least one failure case per implemented function). Put the video link in this README.

If you want, I can:
- run a quick verification script to connect to your DB and run basic queries (needs DB credentials),
- expand the demo CLI to cover all listed functions, or
- convert this to an ORM-based implementation (SQLAlchemy) for the bonus.
# How to run


# Demo video YouTube link


# File structure
```
/project-root 
  /sql 
    DDL.sql        # CREATE TABLE statements with constraints 
    DML.sql        # Sample data (at least 3–5 records per table) 
  /app             # Application source code 
  /docs 
    ERD.pdf        # ER diagram + Mapping + Normalization (required) 
  README.md        # How to run the project, video link
```