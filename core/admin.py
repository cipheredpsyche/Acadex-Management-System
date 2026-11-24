from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ContactMessage, SchoolSettings, Subject, Task, User


@admin.register(User)
class AcadexUserAdmin(UserAdmin):
    list_display = ('school_id', 'full_name', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'section')
    search_fields = ('school_id', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Acadex', {'fields': ('role', 'school_id', 'gender', 'birthdate', 'address', 'contact_number',
                               'photo', 'course', 'academic_year', 'year_level', 'section')}),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'subject', 'due_date', 'status', 'deleted_at')
    list_filter = ('status', 'subject')

    def get_queryset(self, request):
        return Task.all_objects.all()


admin.site.register(Subject)
admin.site.register(SchoolSettings)
admin.site.register(ContactMessage)
