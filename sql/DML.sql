--members
INSERT INTO members (email, full_name, date_of_birth, gender, phone)
VALUES
('alice@example.com','Alice Morgan','1990-05-15','F','+123456789'),
('bob@example.com','Bob Smith','1985-11-02','M','+198765432'),
('carla@example.com','Carla Gomez','1995-03-22','F','+1415555000');

--trainers
INSERT INTO trainers (email, full_name, phone, certification)
VALUES
('tom.trainer@example.com','Tom Trainer','+15550001','CPT Level 3'),
('jane.trainer@example.com','Jane Coach','+15550002','Group Fitness');

-- admins
INSERT INTO admins (email, full_name)
VALUES
('admin1@example.com','Admin One');

-- rooms
INSERT INTO rooms (name, capacity)
VALUES ('Studio A',30), ('Training Room 1',4), ('Main Hall',60);

--equipment
INSERT INTO equipment (name, room_id, status)
VALUES ('Treadmill #1', (SELECT id FROM rooms WHERE name='Studio A'), 'operational'),
       ('Bench Press', (SELECT id FROM rooms WHERE name='Training Room 1'), 'operational');

-- trainer avail (w tstzrange)
-- Tom = avail tmr 09:00-12:00
INSERT INTO trainer_availability (trainer_id, avail_range, note)
VALUES (
  (SELECT id FROM trainers WHERE email='tom.trainer@example.com'),
  tstzrange((now()::date + INTERVAL '1 day') + INTERVAL '09 hours', (now()::date + INTERVAL '1 day') + INTERVAL '12 hours'),
  'Morning block'
);

-- Jane = avail tmr 14:00-17:00
INSERT INTO trainer_availability (trainer_id, avail_range, note)
VALUES (
  (SELECT id FROM trainers WHERE email='jane.trainer@example.com'),
  tstzrange((now()::date + INTERVAL '1 day') + INTERVAL '14 hours', (now()::date + INTERVAL '1 day') + INTERVAL '17 hours'),
  'Afternoon block'
);

--Classes
INSERT INTO classes (name, description, default_capacity)
VALUES ('Yoga','Relaxing Vinyasa yoga',20), ('Spin','High intensity cycling',15);

--class sessions
--yoga class tmr 10:00-11:00 in Studio A by Tom trainer
INSERT INTO class_sessions (class_id, trainer_id, room_id, session_range, capacity)
VALUES (
  (SELECT id FROM classes WHERE name='Yoga'),
  (SELECT id FROM trainers WHERE email='tom.trainer@example.com'),
  (SELECT id FROM rooms WHERE name='Studio A'),
  tstzrange((now()::date + INTERVAL '1 day') + INTERVAL '10 hours', (now()::date + INTERVAL '1 day') + INTERVAL '11 hours'),
  20
);

-- health metrics sample
INSERT INTO health_metrics (member_id, metric_type, metric_value, recorded_at)
VALUES
((SELECT id FROM members WHERE email='alice@example.com'),'weight',72.5, now() - INTERVAL '30 days'),
((SELECT id FROM members WHERE email='alice@example.com'),'weight',71.0, now() - INTERVAL '10 days'),
((SELECT id FROM members WHERE email='bob@example.com'),'weight',85.0, now() - INTERVAL '5 days');

-- fitness goals
INSERT INTO fitness_goals (member_id, goal_type, target_value, units, start_date, end_date, active)
VALUES ((SELECT id FROM members WHERE email='alice@example.com'), 'target_weight', 68.0, 'kg', now()::date - INTERVAL '30 days', now()::date + INTERVAL '60 days', TRUE);


-- create invoice for Bob and item, then payment
INSERT INTO invoices (member_id, total_amount, status)
VALUES ((SELECT id FROM members WHERE email='bob@example.com'), 50.00, 'open');

INSERT INTO invoice_items (invoice_id, description, amount)
VALUES ((SELECT id FROM invoices WHERE member_id = (SELECT id FROM members WHERE email='bob@example.com') ORDER BY created_at DESC LIMIT 1), 'Monthly membership', 50.00);

INSERT INTO payments (invoice_id, amount, method)
VALUES ((SELECT id FROM invoices WHERE member_id = (SELECT id FROM members WHERE email='bob@example.com') ORDER BY created_at DESC LIMIT 1), 50.00, 'cash');
