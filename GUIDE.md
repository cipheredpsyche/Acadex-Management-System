# Acadex (Django) — Step-by-Step Guide

Stack: **Django (Python)** · **SQLite** (Django's built-in database — no XAMPP, no MySQL) · plain HTML/CSS/JavaScript.
Built from your Figma file *MCO1 Figma Output Design* plus your two changes (new **Add Task** popup, new **Date of Birth** picker).

> **Honest note:** the sandbox I built this in could not install Django, so the code has been syntax-checked
> and cross-checked (templates ↔ URLs ↔ views ↔ static files) but **not run**. Run Part A first; if anything errors,
> copy the error to me and I will fix it.

---------------------------------------------------------------------

## PART A — Run it on your computer

1. Install **Python 3.10+** from python.org (tick *“Add Python to PATH”*).
2. Put this project in your repo folder (it uses the same `config/` + `core/` layout as your repo, so you can copy over it).
3. Open a terminal **inside the project folder** (the one containing `manage.py`) and run:

```
py -m venv venv                       # 1. private Python box for this project
venv\Scripts\activate                 # 2. turn it on   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt       # 3. install Django & friends
python manage.py makemigrations core  # 4. turn models.py into database instructions
python manage.py migrate              # 5. create the tables in db.sqlite3
python manage.py seed_demo            # 6. add demo admin, students and tasks
python manage.py runserver            # 7. start the site
```
4. Open **http://127.0.0.1:8000**.

| Role | Login | Password |
|---|---|---|
| Administrator (Kent Valderrama) | `ADMIN001` | `Admin@123` |
| Student (Aki Delos Reyes) | `23000751` | `Student@123` |

You can log in with **School ID or email**. Change these passwords before going live.

### What each page does
| Page | What works |
|---|---|
| Home / About / Contact | Landing page from Figma; Contact saves messages (see them in `/django-admin/`) |
| Log In (account picker → login) | School ID or email + password, eye icon, forgot password, redirect by role |
| Create Account | Email + password + confirm → new student account |
| Student: Dashboard | Greeting banner, Tasks / Due Soon / Complete counts, 4 upcoming tasks |
| Student: My Tasks | **Add Task popup**, click a title to edit, status dropdown, delete → trash bin |
| Student: Subjects | One card per subject with progress bar |
| Student: Progress | Completed/Scheduled subjects, progress bars, next deadlines |
| Profile (both roles) | Photo upload, edit profile, change password |
| Admin: Dashboard | Counts, new students, deactivated accounts, upcoming deadlines |
| Admin: Manage Tasks | All tasks, change status, delete, filter by category |
| Admin: Students | Search, section filter, **Add New Student**, edit, reset password, deactivate/activate, delete |
| Admin: Settings | School info, default priority/status, Manage Categories, Trashbin (restore) |

---------------------------------------------------------------------

## PART B — The database (Django's built-in one)

Django ships with **SQLite**: the whole database is one file, `db.sqlite3`, created by `migrate`. There is nothing to install.

* **Tables are written as Python classes** in `core/models.py`:
  * `User` — students *and* administrators (the `role` field decides which). Holds School ID, birthdate, course, section, photo…
  * `Subject` — a category such as “DBMS 2” (managed by the admin).
  * `Task` — belongs to one student and one subject; has `due_date`, `status`, and `deleted_at` (set = in the trash bin).
  * `SchoolSettings` — one row of school-wide settings. `ContactMessage` — messages from the Contact page.
* `makemigrations` reads the classes and writes a migration file; `migrate` runs it and creates the real tables.
* Passwords are **hashed** by Django (never stored as plain text).
* To look at the data: open **http://127.0.0.1:8000/django-admin/** (log in as ADMIN001), or open `db.sqlite3` with the free *DB Browser for SQLite*.
* Changing a model later? Run `makemigrations` then `migrate` again.

---------------------------------------------------------------------

## PART C — How it was made (step by step)

**1. Read the Figma design** and list the pages: Home, About, Contact, Account picker, Login, Create Account, Forgot Password, then Student (Dashboard, My Tasks, Subjects, Progress, Profile) and Administrator (Dashboard, Manage Tasks, Students, Settings, Profile) plus popups (Add Task, Add/Edit Student, Reset/Deactivate/Delete, Restore).

**2. Create the project** (already done in your repo):
`django-admin startproject config .` and `python manage.py startapp core`.

**3. `config/settings.py`** — registered the `core` app, set `AUTH_USER_MODEL = 'core.User'`, SQLite database, time zone `Asia/Manila`, static/media folders, WhiteNoise (serves CSS when deployed), and read secrets from environment variables so the same code runs locally and online.

**4. `core/models.py`** — wrote the tables (Part B). Two ideas worth learning:
* **Custom user** (`class User(AbstractUser)`): adds role, School ID, birthdate… to Django's login system.
* **Trash bin**: instead of deleting a task we set `deleted_at`. A custom manager `ActiveTaskManager` hides those rows; `Task.all_objects` shows everything (used by the trash page).

**5. `core/backends.py`** — a login backend so people can sign in with **School ID or email**.

**6. `core/forms.py`** — forms validate input (dates not in the future, unique emails/IDs, password strength). `StudentForm` powers *Add New Student*.

**7. `core/views.py`** — one function per page. `@student_required` / `@admin_required` decorators stop a student from opening admin pages. POST views end with `redirect()` so refreshing never re-submits a form. Every task query is filtered by `student=request.user` so students can only touch their own tasks.

**8. `core/urls.py`** — connects addresses (`/tasks/`, `/manage/students/`…) to views. Forgot-password uses Django's built-in views with our templates.

**9. Templates** (`core/templates/core/`) — `base_app.html` is the sidebar layout every logged-in page extends; `base_public.html` is the website navbar/footer. Each page only fills in its `{% block content %}`.

**10. CSS** (`static/core/css/style.css`) — colours sampled from Figma: sidebar `#60021A`, page `#EAE2E2`, cream `#FCF0DC`, inputs `#EADFDF`. Status pills: Pending = blue, In Progress = green, Completed = mauve.

**11. JavaScript** (`static/core/js/app.js`) — popups use the native `<dialog>` element; one shared “Are you sure?” popup serves every delete/deactivate/restore button.

**12. Demo data** (`management/commands/seed_demo.py`) — `python manage.py seed_demo` recreates the Figma students and tasks.

### Your two requested design changes
**A. Add Task popup** (`templates/core/tasks.html`, block `modals`, + `app.js`): the beige rounded popup from your picture — *Add Task* heading in maroon serif, **Subject**, **Task Title**, **Due Date** (`mm/dd/yyyy` with calendar icon), **Status** dropdown (Pending default), **Cancel** + **Add Task**. The same popup is reused for editing (JS changes the title/button and pre-fills the fields). Typing a new subject creates it automatically.

**B. Date of Birth picker** (`templates/core/admin_students.html` + `app.js`): the field uses the browser's calendar (like your picture, with Clear / Today and the month-year dropdown) and also gets:
* a **calendar icon** — clicking the icon or anywhere in the field opens the calendar;
* a **Quick pick** row (Month · Day · Year drop-downs) so the admin can jump straight to a birth year (e.g. 2006) without paging through months. It stays in sync with the calendar and handles short months (Feb 30 → Feb 28/29);
* **future dates blocked** (`max` = today, checked again on the server);
* **Age fills in automatically** (the Figma “Age” dropdown became a read-only field calculated from the birthdate, so it can never disagree).

---------------------------------------------------------------------

## PART D — Put it online (deploy)

SQLite works great for a school project **if the host keeps its disk between restarts**. Recommended: **PythonAnywhere** (free, beginner-friendly, keeps `db.sqlite3`).

### D1. PythonAnywhere (recommended)
1. Push the project to your GitHub repo (`git add . && git commit -m "Django version" && git push`). *Do not commit `db.sqlite3` or `.env`* (`.gitignore` already blocks them).
2. Sign up at pythonanywhere.com → **Consoles → Bash**:
```
git clone https://github.com/cipheredpsyche/Acadex-Management-System.git
cd Acadex-Management-System
mkvirtualenv acadex --python=python3.12      # use a Python version PythonAnywhere lists
pip install -r requirements.txt
```
3. **Web** tab → *Add a new web app* → *Manual configuration* → same Python version. Set:
   * **Source code**: `/home/YOURNAME/Acadex-Management-System`
   * **Virtualenv**: `/home/YOURNAME/.virtualenvs/acadex`
4. Click the **WSGI configuration file** link and replace everything with:
```python
import os, sys
path = '/home/YOURNAME/Acadex-Management-System'
if path not in sys.path:
    sys.path.insert(0, path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DEBUG'] = '0'
os.environ['SECRET_KEY'] = 'paste-a-long-random-string-here'
os.environ['ALLOWED_HOSTS'] = 'YOURNAME.pythonanywhere.com'
os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://YOURNAME.pythonanywhere.com'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
   (Make a secret key with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.)
5. Back in the Bash console (with `DEBUG=0 SECRET_KEY=x` is **not** needed for these commands — they run in debug mode by default):
```
python manage.py makemigrations core
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser        # your real admin (or: python manage.py seed_demo for demo data)
```
   A `createsuperuser` account is automatically an *Administrator* in Acadex.
6. **Web** tab → **Reload**. Visit `https://YOURNAME.pythonanywhere.com`.

### D2. Render.com (alternative)
Render's free disk is wiped on every deploy, so **SQLite data would be lost** — use Render's free **PostgreSQL** instead: create the database, add its URL as the `DATABASE_URL` environment variable, uncomment `psycopg2-binary` in `requirements.txt`, set *Build command* `./build.sh`, *Start command* `gunicorn config.wsgi`, plus `DEBUG=0`, `SECRET_KEY`. (Settings already read `DATABASE_URL` and Render's hostname.)

### D3. Before real students use it
* Change/delete the demo accounts and **never run `seed_demo` on the live site with real data**.
* Set real email (see `.env.example`) so *Forgot password* sends actual emails; until then the email text prints in the server console and **admins can use Students → ⋮ → Reset password**, which shows a temporary password.
* Uploaded profile photos live in `media/`. On free hosts that disk can be wiped — for a bigger site use cloud storage.

---------------------------------------------------------------------

## Known limits / next steps
* **Figma screens I could not see:** my Figma tool hit its free-plan limit before I viewed *View Options*, *Change Password*, *Restore Data*, *Admin Profile* and *Contact/About* in detail — those pages are built in the same style but may differ from your frames. Send screenshots of them and I will match them.
* Facebook/Google/Apple buttons are design placeholders (real social login needs a separate setup).
* Student profile photos in your Figma are sample images; the system shows initials until a photo is uploaded.
