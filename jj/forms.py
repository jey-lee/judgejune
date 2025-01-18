from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Session

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'id': 'email'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name',
            'id': 'name'
        })
    )
    password1 = forms.CharField(
        label="Password",  # Change the label for password1
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",  # Change the label for password2
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'id': 'confirmPassword'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            'name', 'resolution', 'details',
            'aff_speaker1', 'aff_speaker2',
            'con_speaker1', 'con_speaker2',
            'constructive1', 'constructive2',
            'crossfire1', 'rebuttal1', 'rebuttal2', 'crossfire2',
            'summary1', 'summary2', 'grand_crossfire',
            'final_focus1', 'final_focus2',
            'response',
            'transcription','results'
        ]
    
    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.initial is None:
                field.initial = ''
            