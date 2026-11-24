import secrets
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (ContactForm, LoginForm, PhotoForm, ProfileForm, SettingsForm, SignupForm,
                    StudentForm, SubjectForm, TaskForm)
from .models import (SECTIONS, STATUS_DONE, STATUS_PENDING, STATUSES, SchoolSettings, Subject, Task, User)

VALID_STATUSES = [s for s, _ in STATUSES]


# ============================================================ helpers
def role_required(role):
    """Only let logged-in users with this role in; everyone else goes to their own dashboard."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                return redirect('dashboard')
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


student_required = role_required(User.ROLE_STUDENT)
admin_required = role_required(User.ROLE_ADMIN)


def first_error(form):
    """One readable error message from a form."""
    for field, errs in form.errors.items():
        label = form.fields[field].label if field in form.fields and form.fields[field].label else field
        return f"{str(label).replace('_', ' ').capitalize()}: {errs[0]}" if field != '__all__' else errs[0]
    return 'Please check the form and try again.'


def get_subject(name):
    """Find a subject (case-insensitive) or create it."""
    return Subject.objects.filter(name__iexact=name).first() or Subject.objects.create(name=name)


# ============================================================ public pages
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Thank you! Your message was sent.')
        return redirect('contact')
    return render(request, 'core/contact.html', {'form': form})


def select_account(request):
    return render(request, 'core/select_account.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        login(request, form.user)
        nxt = request.GET.get('next', '')
        if nxt.startswith('/') and not nxt.startswith('//'):
            return redirect(nxt)
        return redirect('dashboard')
    return render(request, 'core/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        user = User(email=email, username=email, role=User.ROLE_STUDENT, first_name=email.split('@')[0])
        user.set_password(form.cleaned_data['password'])
        user.save()
        login(request, user)
        messages.success(request, 'Welcome to Acadex! You can complete your profile anytime.')
        return redirect('dashboard')
    return render(request, 'core/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ============================================================ dashboard router
@login_required
def dashboard(request):
    return admin_dashboard(request) if request.user.is_admin_role else student_dashboard(request)


# ============================================================ STUDENT
@student_required
def student_dashboard(request):
    tasks = Task.objects.filter(student=request.user)
    today = date.today()
    ctx = {
        'total': tasks.count(),
        'due_soon': tasks.exclude(status=STATUS_DONE).filter(due_date__range=(today, today + timedelta(days=7))).count(),
        'complete': tasks.filter(status=STATUS_DONE).count(),
        'upcoming': tasks.exclude(status=STATUS_DONE).select_related('subject').order_by('due_date')[:4],
    }
    return render(request, 'core/student_dashboard.html', ctx)


@student_required
def tasks(request):
    qs = Task.objects.filter(student=request.user).select_related('subject')
    return render(request, 'core/tasks.html', {
        'tasks': qs,
        'status_choices': STATUSES,
        'subject_names': Subject.objects.values_list('name', flat=True),
        'default_status': SchoolSettings.load().default_status,
        'trash_count': Task.all_objects.filter(student=request.user, deleted_at__isnull=False).count(),
    })


@student_required
@require_POST
def task_save(request, pk=None):
    form = TaskForm(request.POST)
    if not form.is_valid():
        messages.error(request, first_error(form))
        return redirect('tasks')
    d = form.cleaned_data
    subject = get_subject(d['subject'])
    if pk:
        task = get_object_or_404(Task, pk=pk, student=request.user)
        task.subject, task.title, task.due_date, task.status = subject, d['title'], d['due_date'], d['status']
        task.save()
        messages.success(request, 'Task updated.')
    else:
        Task.objects.create(student=request.user, subject=subject, title=d['title'], due_date=d['due_date'],
                            status=d['status'], priority=SchoolSettings.load().default_priority)
        messages.success(request, 'Task added.')
    return redirect('tasks')


@login_required
@require_POST
def task_status(request, pk):
    """Changes a task's status (students: own tasks, admin: any task)."""
    qs = Task.objects.all() if request.user.is_admin_role else Task.objects.filter(student=request.user)
    task = get_object_or_404(qs, pk=pk)
    status = request.POST.get('status')
    if status in VALID_STATUSES:
        task.status = status
        task.save(update_fields=['status'])
        messages.success(request, f'Status changed to {status}.')
    return redirect('admin_tasks' if request.user.is_admin_role else 'tasks')


@login_required
@require_POST
def task_delete(request, pk):
    """Moves a task to the trash bin (it can be restored)."""
    qs = Task.objects.all() if request.user.is_admin_role else Task.objects.filter(student=request.user)
    get_object_or_404(qs, pk=pk).move_to_trash()
    messages.success(request, 'Task moved to the trash bin.')
    return redirect('admin_tasks' if request.user.is_admin_role else 'tasks')


@student_required
def subjects(request):
    rows = (Subject.objects
            .filter(tasks__student=request.user, tasks__deleted_at__isnull=True)
            .annotate(total=Count('tasks', filter=Q(tasks__student=request.user, tasks__deleted_at__isnull=True)),
                      done=Count('tasks', filter=Q(tasks__student=request.user, tasks__deleted_at__isnull=True,
                                                   tasks__status=STATUS_DONE)))
            .distinct())
    cards = [{'name': s.name, 'total': s.total, 'done': s.done,
              'pct': round(s.done / s.total * 100) if s.total else 0} for s in rows]
    return render(request, 'core/subjects.html', {'cards': cards})


@student_required
def progress(request):
    mine = Task.objects.filter(student=request.user)
    rows = (Subject.objects.filter(tasks__student=request.user, tasks__deleted_at__isnull=True)
            .annotate(total=Count('tasks', filter=Q(tasks__student=request.user, tasks__deleted_at__isnull=True)),
                      done=Count('tasks', filter=Q(tasks__student=request.user, tasks__deleted_at__isnull=True,
                                                   tasks__status=STATUS_DONE)))
            .distinct())
    bars = [{'name': s.name, 'pct': round(s.done / s.total * 100) if s.total else 0} for s in rows]
    ctx = {
        'completed_subjects': sum(1 for s in rows if s.total and s.done == s.total),
        'scheduled_subjects': len(bars),
        'bars': bars[:5],
        'deadlines': mine.exclude(status=STATUS_DONE).filter(due_date__gte=date.today())
                         .select_related('subject').order_by('due_date')[:3],
        'semester': SchoolSettings.load().current_semester,
    }
    return render(request, 'core/progress.html', ctx)


# ============================================================ trash (shared)
@login_required
def trash(request):
    qs = Task.all_objects.filter(deleted_at__isnull=False).select_related('subject', 'student')
    if not request.user.is_admin_role:
        qs = qs.filter(student=request.user)
    return render(request, 'core/trash.html', {'tasks': qs.order_by('-deleted_at')})


def _trashed_task(request, pk):
    qs = Task.all_objects.filter(deleted_at__isnull=False)
    if not request.user.is_admin_role:
        qs = qs.filter(student=request.user)
    return get_object_or_404(qs, pk=pk)


@login_required
@require_POST
def task_restore(request, pk):
    _trashed_task(request, pk).restore()
    messages.success(request, 'Task restored.')
    return redirect('trash')


@login_required
@require_POST
def task_purge(request, pk):
    _trashed_task(request, pk).delete()
    messages.success(request, 'Task permanently deleted.')
    return redirect('trash')


# ============================================================ profile (shared)
@login_required
def profile(request):
    stats = {}
    if not request.user.is_admin_role:
        mine = Task.objects.filter(student=request.user)
        stats = {'total': mine.count(), 'done': mine.filter(status=STATUS_DONE).count()}
    return render(request, 'core/profile.html', {
        'form': ProfileForm(instance=request.user),
        'pw_form': PasswordChangeForm(request.user),
        'stats': stats,
        'open_modal': request.GET.get('open', ''),
    })


@login_required
@require_POST
def profile_edit(request):
    form = ProfileForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
    else:
        messages.error(request, first_error(form))
    return redirect('profile')


@login_required
@require_POST
def profile_photo(request):
    form = PhotoForm(request.POST, request.FILES, instance=request.user)
    if form.is_valid() and request.FILES.get('photo'):
        form.save()
        messages.success(request, 'Photo updated.')
    else:
        messages.error(request, 'Please choose a valid image file.')
    return redirect('profile')


@login_required
@require_POST
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)       # keeps the user logged in
        messages.success(request, 'Password changed.')
    else:
        messages.error(request, first_error(form))
    return redirect('profile')


# ============================================================ ADMIN
def _task_counts():
    qs = Task.objects.all()
    return {
        'students': User.objects.filter(role=User.ROLE_STUDENT).count(),
        'active': qs.exclude(status=STATUS_DONE).count(),
        'completed': qs.filter(status=STATUS_DONE).count(),
        'pending': qs.filter(status=STATUS_PENDING).count(),
    }


@admin_required
def admin_dashboard(request):
    students = User.objects.filter(role=User.ROLE_STUDENT)
    ctx = _task_counts()
    ctx.update({
        'new_students': students.order_by('-date_joined')[:5],
        'deactivated': students.filter(is_active=False).order_by('-date_joined')[:5],
        'deadlines': Task.objects.exclude(status=STATUS_DONE).filter(due_date__gte=date.today())
                         .select_related('subject').order_by('due_date')[:5],
    })
    return render(request, 'core/admin_dashboard.html', ctx)


@admin_required
def admin_tasks(request):
    qs = Task.objects.select_related('subject', 'student')
    current = request.GET.get('subject', '')
    if current:
        qs = qs.filter(subject__name=current)
    ctx = _task_counts()
    ctx.update({
        'tasks': qs.order_by('due_date')[:100],
        'categories': Subject.objects.annotate(n=Count('tasks', filter=Q(tasks__deleted_at__isnull=True)))
                             .order_by('-n', 'name')[:4],
        'current': current,
        'status_choices': STATUSES,
    })
    return render(request, 'core/admin_tasks.html', ctx)


def _students_context(request, form=None, form_action=None, open_form=False):
    students = User.objects.filter(role=User.ROLE_STUDENT)
    base = students
    q = request.GET.get('q', '').strip()
    section = request.GET.get('section', '')
    if q:
        students = students.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                                   Q(school_id__icontains=q) | Q(email__icontains=q))
    if section in [s for s, _ in SECTIONS]:
        students = students.filter(section=section)
    students = students.annotate(
        total=Count('tasks', filter=Q(tasks__deleted_at__isnull=True)),
        done=Count('tasks', filter=Q(tasks__deleted_at__isnull=True, tasks__status=STATUS_DONE)))
    cards = [{'u': s, 'pct': round(s.done / s.total * 100) if s.total else 0} for s in students]
    return {
        'cards': cards, 'q': q, 'section': section, 'sections': SECTIONS,
        'total_students': base.count(),
        'active_students': base.filter(is_active=True).count(),
        'inactive_students': base.filter(is_active=False).count(),
        'form': form or StudentForm(), 'form_action': form_action, 'open_form': open_form,
        'reset_info': request.session.pop('reset_info', None),
    }


@admin_required
def admin_students(request):
    return render(request, 'core/admin_students.html', _students_context(request))


@admin_required
@require_POST
def student_save(request, pk=None):
    instance = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT) if pk else None
    form = StudentForm(request.POST, instance=instance)
    if form.is_valid():
        user = form.save()
        messages.success(request, f'{user.full_name} was {"updated" if pk else "added"}.')
        return redirect('admin_students')
    from django.urls import reverse
    action = reverse('student_edit', args=[pk]) if pk else reverse('student_add')
    ctx = _students_context(request, form=form, form_action=action, open_form=True)
    ctx['edit_title'] = 'Edit Student' if pk else 'Add New Student'
    return render(request, 'core/admin_students.html', ctx)


@admin_required
@require_POST
def student_toggle(request, pk):
    u = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT)
    u.is_active = not u.is_active
    u.save(update_fields=['is_active'])
    messages.success(request, f'{u.full_name} was {"activated" if u.is_active else "deactivated"}.')
    return redirect('admin_students')


@admin_required
@require_POST
def student_delete(request, pk):
    u = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT)
    name = u.full_name
    u.delete()
    messages.success(request, f'{name} was deleted.')
    return redirect('admin_students')


@admin_required
@require_POST
def student_reset(request, pk):
    """Gives the student a new temporary password and emails it (if email is set up)."""
    u = get_object_or_404(User, pk=pk, role=User.ROLE_STUDENT)
    temp = 'Acadex-' + secrets.token_hex(3)
    u.set_password(temp)
    u.save()
    send_mail('Your Acadex password was reset',
              f'Hello {u.full_name},\n\nYour temporary Acadex password is: {temp}\n'
              'Please log in and change it from your Profile page.\n',
              None, [u.email], fail_silently=True)
    request.session['reset_info'] = {'name': u.full_name, 'email': u.email, 'password': temp}
    return redirect('admin_students')


@admin_required
def admin_settings(request):
    instance = SchoolSettings.load()
    form = SettingsForm(request.POST or None, instance=instance)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved.')
            return redirect('admin_settings')
        messages.error(request, first_error(form))
    return render(request, 'core/admin_settings.html', {
        'form': form, 'trash_count': Task.all_objects.filter(deleted_at__isnull=False).count()})


@admin_required
def categories(request):
    rows = Subject.objects.annotate(n=Count('tasks', filter=Q(tasks__deleted_at__isnull=True)))
    return render(request, 'core/categories.html', {'rows': rows})


@admin_required
@require_POST
def category_save(request, pk=None):
    form = SubjectForm(request.POST, instance=get_object_or_404(Subject, pk=pk) if pk else None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Category saved.')
    else:
        messages.error(request, first_error(form))
    return redirect('categories')


@admin_required
@require_POST
def category_delete(request, pk):
    get_object_or_404(Subject, pk=pk).delete()
    messages.success(request, 'Category and its tasks were deleted.')
    return redirect('categories')
