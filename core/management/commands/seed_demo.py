"""
python manage.py seed_demo

Creates demo data that mirrors the Figma design:
  Admin    -> ADMIN001    / Admin@123      (Kent Valderrama)
  Students -> 23000751 .. 23000757 / Student@123   (Aki Delos Reyes is 23000751)
Safe to run more than once (it will not duplicate users).
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from core.models import SchoolSettings, Subject, Task, User

ADMIN_PASSWORD = 'Admin@123'
STUDENT_PASSWORD = 'Student@123'

SUBJECTS = ['Web Sys', 'SIA 1', 'Platform Tech', 'DBMS 2', 'HCI 2', 'Entrepreneurship', 'Appdev 1', 'QM']

# full name, school id, course, year level, section, birthdate, gender, tasks done / total
STUDENTS = [
    ('Aki Delos Reyes', '23000751', 'BS Information Technology', '3rd', 'A', date(2006, 6, 27), 'Female', (2, 7)),
    ('Jhanyne Tajantajan', '23000752', 'BS Information Technology', '3rd', 'A', date(2005, 3, 14), 'Female', (8, 10)),
    ('Lei Vergara', '23000753', 'BS Information Technology', '3rd', 'C', date(2005, 9, 2), 'Male', (4, 10)),
    ('Athallyah Mendoza', '23000754', 'BS Computer Science', '2nd', 'A', date(2006, 1, 21), 'Female', (7, 10)),
    ('Sean Dela Cruz', '23000755', 'BS Information Technology', '3rd', 'C', date(2005, 11, 8), 'Male', (1, 10)),
    ('Athena Dizon', '23000756', 'BS Computer Science', '1st', 'A', date(2007, 5, 30), 'Female', (8, 10)),
    ('Kenji Castillano', '23000757', 'BS Computer Science', '2nd', 'C', date(2006, 8, 12), 'Male', (3, 10)),
]

# Aki's tasks (title, subject, days from today, status) - same as the Figma screens
AKI_TASKS = [
    ('Finish Figma', 'Web Sys', -12, 'Completed'),
    ('Chapter 1', 'SIA 1', -4, 'Completed'),
    ('OS installation', 'Platform Tech', 3, 'Pending'),
    ('Query Warmup', 'DBMS 2', 5, 'In Progress'),
    ('Case Study Draft', 'Web Sys', 9, 'Pending'),
    ('Windows vs. Linux Report', 'Platform Tech', 18, 'Pending'),
    ('Essay Writing', 'Entrepreneurship', 26, 'Pending'),
]

TITLES = ['Reading Quiz', 'Lab Activity', 'Prototype Demo', 'Case Study', 'Group Report', 'Wireframe',
          'Chapter Summary', 'Midterm Review', 'Presentation', 'Reflection Paper']


class Command(BaseCommand):
    help = 'Create demo users, subjects and tasks.'

    def handle(self, *args, **options):
        SchoolSettings.load()
        subjects = {n: Subject.objects.get_or_create(name=n)[0] for n in SUBJECTS}
        today = date.today()

        admin, created = User.objects.get_or_create(
            school_id='ADMIN001',
            defaults=dict(username='ADMIN001', email='admin@acadex.local', first_name='Kent',
                          last_name='Valderrama', role=User.ROLE_ADMIN, is_staff=True, is_superuser=True,
                          contact_number='0917 123 4567', address='Kidapawan City, 9400, North Cotabato, PH'))
        if created:
            admin.set_password(ADMIN_PASSWORD)
            admin.save()

        names = list(subjects)
        for i, (full, sid, course, year, section, born, gender, (done, total)) in enumerate(STUDENTS):
            first, last = full.rsplit(' ', 1)
            first = full[: -len(last)].strip()
            user, created = User.objects.get_or_create(
                school_id=sid,
                defaults=dict(username=sid, email=f"{full.split()[0].lower()}{sid[-2:]}@acadex.local",
                              first_name=first, last_name=last, role=User.ROLE_STUDENT, birthdate=born,
                              gender=gender, course=course, academic_year='2026 - 2027', year_level=year,
                              section=section, contact_number='0994 931 4122',
                              address='Kidapawan City, 9400, North Cotabato, PH'))
            if not created:
                continue
            user.set_password(STUDENT_PASSWORD)
            user.save()
            if i == 0:
                for title, subj, offset, status in AKI_TASKS:
                    Task.objects.create(student=user, subject=subjects[subj], title=title,
                                        due_date=today + timedelta(days=offset), status=status)
            else:
                for n in range(total):
                    Task.objects.create(
                        student=user, subject=subjects[names[(i + n) % len(names)]],
                        title=f'{TITLES[n % len(TITLES)]} {n + 1}',
                        due_date=today + timedelta(days=(n * 3) - 6 + i),
                        status='Completed' if n < done else ('In Progress' if n % 2 else 'Pending'))

        # two deactivated accounts, as in the Figma dashboard
        for full, sid in [('Shena De Vera', '23000760'), ('Jillian Santos', '23000761')]:
            first, last = full.rsplit(' ', 1)
            u, created = User.objects.get_or_create(
                school_id=sid, defaults=dict(username=sid, email=f'{first.lower()}{sid[-2:]}@acadex.local',
                                             first_name=first, last_name=last, is_active=False,
                                             course='BS Information Technology', year_level='4th', section='B'))
            if created:
                u.set_password(STUDENT_PASSWORD)
                u.save()

        self.stdout.write(self.style.SUCCESS(
            'Demo data ready.  Admin: ADMIN001 / Admin@123   Student: 23000751 / Student@123'))
