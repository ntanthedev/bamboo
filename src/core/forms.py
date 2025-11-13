from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import InviteCode, Answer
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Tên tài khoản', 'class': 'form-control', 'id': 'name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email của bạn', 'class': 'form-control', 'id': 'email'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Mật khẩu', 'class': 'form-control', 'id': 'password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập lại mật khẩu', 'class': 'form-control', 'id': 'repeat-password'})
    )
    invite_code = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Mã mời', 'class': 'form-control', 'id': 'invite-code'})
    )
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'id': 'terms'})
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'remember'})
    )
    
    class Meta:
        model = User
        fields = ("name", "email", "password1", "password2", "invite_code", "accept_terms", "remember_me")
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email này đã được sử dụng.")
        return email
    
    def clean_invite_code(self):
        code = self.cleaned_data.get('invite_code')
        if not code:
            return None
            
        try:
            referral = InviteCode.objects.get(code=code, is_active=True)
            if referral.remaining_uses <= 0:
                raise ValidationError("Mã giới thiệu này đã hết lượt sử dụng.")
            return referral
        except InviteCode.DoesNotExist:
            raise ValidationError("Mã giới thiệu không hợp lệ hoặc đã hết hạn.")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["name"]
        user.username = self.cleaned_data["email"].split('@')[0]
        
        if commit:
            user.save()
            
            invite_code = self.cleaned_data.get('invite_code')
            if invite_code:
                profile = user.profile
                profile.invite_code = invite_code
                profile.save()
                
                invite_code.use_code()
                
        return user 

class QuizForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super(QuizForm, self).__init__(*args, **kwargs)
        self.questions = questions
        if questions:
            for i, question in enumerate(questions):
                field_name = f'question_{question.id}'
                choices = [(ans.id, ans.text) for ans in question.answer_set.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    required=False,
                    choices=choices,
                    widget=forms.RadioSelect
                )
                self.fields[field_name].question = question

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data 