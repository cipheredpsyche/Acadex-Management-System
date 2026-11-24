from datetime import date

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import (STATUSES, ContactMessage, SchoolSettings, Subject, User)


class StyledForm(forms.Form):
    """Adds the 'input' CSS class to every field so it matches the Figma inputs."""

    def _style(self):
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'input')


# ------------------------------------------------------------ login / signup
class LoginForm(StyledForm):
    username = forms.CharField(label='School ID / Email Address',
                               widget=forms.TextInput(attrs={'placeholder': 'Enter your school ID or Email',
                                                             'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'}))

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None
        self._style()

    def clean(self):
        data = super().clean()
        if data.get('username') and data.get('password'):
            self.user = authenticate(self.request, username=data['username'], password=data['password'])
            if self.user is None:
                raise forms.ValidationError(
                    'Incorrect School ID / Email or password, or the account is deactivated.')
        return data


class SignupForm(StyledForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        data = super().clean()
        pw, confirm = data.get('password'), data.get('confirm')
        if pw and confirm and pw != confirm:
            self.add_error('confirm', 'Passwords do not match.')
        elif pw:
            validate_password(pw)
        return data


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'input'


# --------------------------------------------------------------------- tasks
class TaskForm(StyledForm):
    subject = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Enter Subject',
                                                                            'list': 'subjectList'}))
    title = forms.CharField(max_length=150, label='Task Title',
                            widget=forms.TextInput(attrs={'placeholder': 'Enter task title'}))
    due_date = forms.DateField(label='Due Date', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    status = forms.ChoiceField(choices=STATUSES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_subject(self):
        return ' '.join(self.cleaned_data['subject'].split())


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']

    def clean_name(self):
        name = ' '.join(self.cleaned_data['name'].split())
        qs = Subject.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('That category already exists.')
        return name


# ---------------------------------------------------------------- students
class _FullNameMixin:
    def _split_name(self, user):
        parts = self.cleaned_data['full_name'].strip().rsplit(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) == 2 else ''


class StudentForm(_FullNameMixin, forms.ModelForm):
    """Admin: Add New Student / Edit Student."""
    full_name = forms.CharField(max_length=120)
    password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = User
        fields = ['gender', 'birthdate', 'address', 'email', 'contact_number',
                  'course', 'academic_year', 'year_level', 'section', 'school_id']
        widgets = {'birthdate': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['gender', 'birthdate', 'address', 'email', 'contact_number', 'course',
                     'academic_year', 'year_level', 'section', 'school_id']:
            self.fields[name].required = True
        self.fields['birthdate'].widget.attrs['max'] = date.today().isoformat()
        self.fields['birthdate'].widget.attrs['min'] = '1920-01-01'
        self.fields['password'].widget.attrs['autocomplete'] = 'new-password'
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'input')
        self.order_fields(['full_name', 'gender', 'birthdate', 'address', 'email', 'contact_number',
                           'course', 'academic_year', 'year_level', 'section', 'password', 'school_id'])

    def clean_birthdate(self):
        d = self.cleaned_data['birthdate']
        if d > date.today() or d.year < 1920:
            raise forms.ValidationError('Choose a valid date of birth (not in the future).')
        return d

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_password(self):
        pw = self.cleaned_data.get('password', '')
        if not self.instance.pk and not pw:
            raise forms.ValidationError('Set a password for the new student.')
        if pw:
            validate_password(pw)
        return pw

    def save(self, commit=True):
        user = super().save(commit=False)
        self._split_name(user)
        user.role = User.ROLE_STUDENT
        user.username = user.school_id or user.email
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ProfileForm(_FullNameMixin, forms.ModelForm):
    """Edit My Profile (students and admins)."""
    full_name = forms.CharField(max_length=120)

    class Meta:
        model = User
        fields = ['gender', 'birthdate', 'address', 'email', 'contact_number']
        widgets = {'birthdate': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].initial = self.instance.full_name
        self.fields['birthdate'].widget.attrs['max'] = date.today().isoformat()
        if self.instance.role == User.ROLE_ADMIN:
            del self.fields['gender']
            del self.fields['birthdate']
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'input')
        self.order_fields(['full_name', 'gender', 'birthdate', 'address', 'email', 'contact_number'])

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        self._split_name(user)
        if commit:
            user.save()
        return user


class PhotoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['photo']


class SettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolSettings
        fields = ['institution_name', 'academic_year', 'current_semester', 'default_priority', 'default_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'input'
