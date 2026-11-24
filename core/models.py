import json
from datetime import date

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# ---------- choice lists (also used by the forms) ----------
GENDERS = [('Female', 'Female'), ('Male', 'Male'), ('Other', 'Other')]
COURSES = [(c, c) for c in ['BS Information Technology', 'BS Computer Science']]
ACADEMIC_YEARS = [(y, y) for y in ['2025 - 2026', '2026 - 2027', '2027 - 2028']]
YEAR_LEVELS = [(y, y) for y in ['1st', '2nd', '3rd', '4th']]
SECTIONS = [(s, s) for s in ['A', 'B', 'C', 'D']]
SEMESTERS = [(s, s) for s in ['1st Semester', '2nd Semester', 'Summer']]

STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE = 'Pending', 'In Progress', 'Completed'
STATUSES = [(s, s) for s in (STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE)]
PRIORITIES = [(p, p) for p in ('Low', 'Medium', 'High')]


class User(AbstractUser):
    """One user table for both students and administrators (role decides which)."""
    ROLE_STUDENT, ROLE_ADMIN = 'student', 'admin'
    ROLES = [(ROLE_STUDENT, 'Student'), (ROLE_ADMIN, 'Administrator')]

    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default=ROLE_STUDENT)
    school_id = models.CharField('School ID', max_length=30, unique=True, null=True, blank=True)

    # personal information
    gender = models.CharField(max_length=10, choices=GENDERS, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=200, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True)

    # academic information (students)
    course = models.CharField(max_length=100, choices=COURSES, blank=True)
    academic_year = models.CharField(max_length=20, choices=ACADEMIC_YEARS, blank=True)
    year_level = models.CharField(max_length=5, choices=YEAR_LEVELS, blank=True)
    section = models.CharField(max_length=2, choices=SECTIONS, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.ROLE_ADMIN
        if not self.school_id:
            self.school_id = None
        if not self.username:
            self.username = self.school_id or self.email
        super().save(*args, **kwargs)

    # ---- helpers used by templates ----
    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    @property
    def full_name(self):
        return (self.first_name + ' ' + self.last_name).strip() or self.email

    @property
    def initials(self):
        parts = self.full_name.split()
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')).upper()

    @property
    def age(self):
        if not self.birthdate:
            return None
        t = date.today()
        return t.year - self.birthdate.year - ((t.month, t.day) < (self.birthdate.month, self.birthdate.day))

    @property
    def course_code(self):
        """'BS Information Technology' -> 'BSIT'"""
        words = self.course.split()
        if not words:
            return ''
        return words[0] + ''.join(w[0] for w in words[1:])

    @property
    def class_label(self):
        """'BSIT 3-A' as shown on the student cards"""
        if not self.course:
            return ''
        return f"{self.course_code} {self.year_level[:1]}-{self.section}".strip()

    @property
    def edit_json(self):
        """Used by the Edit Student popup to fill in the form."""
        return json.dumps({
            'full_name': self.full_name, 'gender': self.gender,
            'birthdate': self.birthdate.isoformat() if self.birthdate else '',
            'address': self.address, 'email': self.email, 'contact_number': self.contact_number,
            'course': self.course, 'academic_year': self.academic_year,
            'year_level': self.year_level, 'section': self.section,
            'school_id': self.school_id or '',
        })


class Subject(models.Model):
    """A subject / category (managed by the admin, e.g. 'DBMS 2')."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ActiveTaskManager(models.Manager):
    """Default manager: hides tasks that are in the trash bin."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Task(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=150)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default='Medium')
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)   # set = task is in the trash bin

    objects = ActiveTaskManager()      # normal queries -> only active tasks
    all_objects = models.Manager()     # includes trashed tasks

    class Meta:
        ordering = ['due_date', 'id']

    def __str__(self):
        return self.title

    @property
    def status_class(self):
        return {'Pending': 'pending', 'In Progress': 'progress', 'Completed': 'done'}[self.status]

    @property
    def is_overdue(self):
        return self.status != STATUS_DONE and self.due_date < date.today()

    def move_to_trash(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])


class SchoolSettings(models.Model):
    """Single row of school-wide settings (Admin > Settings)."""
    institution_name = models.CharField(max_length=150, default='Colegio de Kidapawan, Inc.')
    academic_year = models.CharField(max_length=20, choices=ACADEMIC_YEARS, default='2026 - 2027')
    current_semester = models.CharField(max_length=20, choices=SEMESTERS, default='1st Semester')
    default_priority = models.CharField(max_length=10, choices=PRIORITIES, default='Medium')
    default_status = models.CharField(
        max_length=20, choices=[(STATUS_PENDING, 'Pending'), (STATUS_PROGRESS, 'In Progress')],
        default=STATUS_PENDING)

    class Meta:
        verbose_name_plural = 'School settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ContactMessage(models.Model):
    """Messages sent from the public Contact page."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} <{self.email}>'
