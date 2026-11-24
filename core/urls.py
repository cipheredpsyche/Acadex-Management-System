from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    # ---- public
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('account/', views.select_account, name='select_account'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # ---- forgot password (Django's built-in views, our templates)
    path('forgot-password/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        success_url=reverse_lazy('password_reset_done')), name='password_reset'),
    path('forgot-password/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # ---- both roles
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/photo/', views.profile_photo, name='profile_photo'),
    path('profile/password/', views.change_password, name='change_password'),
    path('trash/', views.trash, name='trash'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/restore/', views.task_restore, name='task_restore'),
    path('tasks/<int:pk>/purge/', views.task_purge, name='task_purge'),

    # ---- student
    path('tasks/', views.tasks, name='tasks'),
    path('tasks/add/', views.task_save, name='task_add'),
    path('tasks/<int:pk>/edit/', views.task_save, name='task_edit'),
    path('tasks/<int:pk>/status/', views.task_status, name='task_status'),
    path('subjects/', views.subjects, name='subjects'),
    path('progress/', views.progress, name='progress'),

    # ---- administrator
    path('manage/tasks/', views.admin_tasks, name='admin_tasks'),
    path('manage/students/', views.admin_students, name='admin_students'),
    path('manage/students/add/', views.student_save, name='student_add'),
    path('manage/students/<int:pk>/edit/', views.student_save, name='student_edit'),
    path('manage/students/<int:pk>/toggle/', views.student_toggle, name='student_toggle'),
    path('manage/students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('manage/students/<int:pk>/reset/', views.student_reset, name='student_reset'),
    path('manage/settings/', views.admin_settings, name='admin_settings'),
    path('manage/categories/', views.categories, name='categories'),
    path('manage/categories/add/', views.category_save, name='category_add'),
    path('manage/categories/<int:pk>/edit/', views.category_save, name='category_edit'),
    path('manage/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]
