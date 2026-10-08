# CampusCare

A desktop complaint management system for campus facilities. Students report problems (a broken AC, bad Wi-Fi, a leaking pipe) and track them until they are fixed. Administrators see every complaint in one place, assign it to a department and update its status.

Built with Python, Tkinter and SQLite. It needs no third-party packages.

## Features

**Students**
- Sign up for an account from the login page, then log in
- Submit a complaint with a category, a location and a description (10 to 500 characters)
- Get a complaint ID such as `CC-0007` to keep for reference
- Track complaints in the **My Complaints** tab: filter by status, search by ID, category or location
- See a progress tracker (Pending → In Progress → Resolved), the department handling the complaint, and the full status history

**Administrators**
- Dashboard cards showing total, pending, in-progress and resolved complaints
- Table of all complaints, filterable by status and category, with search across student, category, location, description, department and ID
- Assign a complaint to a department and update its status
- Every status change is recorded in the complaint's history

## Requirements

- Python 3 (developed on 3.13)
- Tkinter, which is included with the standard Python installers for Windows and macOS
  - On Debian/Ubuntu Linux, install it with `sudo apt install python3-tk`

## Getting started

```bash
git clone https://github.com/saswatachakrabarti/campuscare.git
cd campuscare
python main.py
```

On first run the app creates its database and, if there are no users yet, two default accounts:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@campus.edu` | `admin123` |
| Student | `student@campus.edu` | `student123` |

**Change or remove these before using the app for anything real.**

## Using the app

### Students
1. On the login page click **Create an account**, fill in your name, email and a password of at least 6 characters, then click **Sign up**.
2. Log in with your new account.
3. In **New Complaint**, pick a category, enter where the problem is and describe it, then click **Submit Complaint**.
4. Open **My Complaints** to follow its progress.

### Administrators
1. Log in with an admin account.
2. Select a complaint in the table to see its details.
3. Choose a department and a status, then click **Save Changes**.

Admin accounts cannot be created from the signup page. To add one, run this from the project folder:

```bash
python -c "import database; database.create_tables(); database.add_user('Your Name', 'you@campus.edu', 'a-strong-password', 'admin')"
```

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Entry point. Sets up the database, shows the login screen and sends each user to the student or admin screen. |
| `login.py` | Login and student signup screens. |
| `complaint.py` | Student dashboard: submit complaints and track them. |
| `admin.py` | Admin dashboard: statistics, filtering, department assignment and status updates. |
| `database.py` | Data layer. All SQLite access goes through this file. |
| `campuscare.db` | SQLite database file, created next to the scripts. |

Each screen can also be run on its own for quick testing: `python login.py`, `python complaint.py` or `python admin.py`.

## Database

SQLite, with three tables:

- **Users**: `user_id`, `name`, `email` (unique), `password` (SHA-256 hash), `role` (`student` or `admin`)
- **Complaints**: `complaint_id`, `user_id`, `category`, `location`, `description`, `status`, `department`, `created_at`
- **Complaint_History**: `history_id`, `complaint_id`, `old_status`, `new_status`, `changed_at`

To start fresh, close the app and delete `campuscare.db`. It is recreated on the next run.

## Reference values

- **Statuses:** Pending, In Progress, Resolved
- **Categories:** Classroom, Laboratory, Hostel, Electrical, Air Conditioning, Furniture, Cleanliness, Internet
- **Departments:** Unassigned, Electrical, Civil / Maintenance, IT / Network, Housekeeping, Air Conditioning, Hostel Administration

These lists are defined at the top of `admin.py` if you want to change them.

## Security notes

This is a learning and demo project, not a hardened system.

- Passwords are hashed with plain SHA-256 and no salt. For real use, switch to a salted, slow hash such as bcrypt or argon2.
- The default admin password is public in this repository, so change it.
- There is no password reset. Users who forget their password need an administrator to update the database.
- `campuscare.db` contains account data, so avoid committing a database that holds real users.
