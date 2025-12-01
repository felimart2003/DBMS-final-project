# Health & Fitness Club Management System
COMP 3005 final project using a PostgreSQL-based schema and a Python demo for a Health and Fitness Club Management System. The project includes database design (DDL), sample data (DML), and operations for Members, Trainers, and Admins.

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

# How to run
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

### Side note: 
We used tstzrange and PostgreSQL exclusion to ensure there were no overlapping bookings with trainers and rooms. 
We included member_dashboard view.
We used a trigger to make sure personal sessions are in trainer avail.