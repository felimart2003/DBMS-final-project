ERD Placeholder

Create an ER diagram (ERD.pdf) showing these entities and relationships:
- members (1) - (N) fitness_goals
- members (1) - (N) health_metrics
- trainers (1) - (N) trainer_availability
- trainers (1) - (N) personal_sessions
- members (1) - (N) personal_sessions
- classes (1) - (N) class_sessions
- class_sessions (1) - (N) class_registrations -> members
- rooms (1) - (N) class_sessions
- rooms (1) - (N) personal_sessions
- equipment (N) - (1) rooms
- equipment (1) - (N) equipment_maintenance

Please export a PDF named `ERD.pdf` and place it in this `docs/` folder before submission.
