from django import forms

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    # 스팸 봇용 honeypot: 사람에게는 보이지 않으며, 값이 들어오면 스팸으로 취급한다
    website = forms.CharField(
        required=False,
        label="웹사이트",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "홍길동"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
            "subject": forms.TextInput(attrs={"placeholder": "문의 제목"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "문의 내용을 자세히 적어 주세요."}),
        }
        error_messages = {
            "name": {"required": "이름을 입력해 주세요."},
            "email": {"required": "이메일을 입력해 주세요.", "invalid": "올바른 이메일 형식이 아닙니다."},
            "subject": {"required": "제목을 입력해 주세요."},
            "message": {"required": "내용을 입력해 주세요."},
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_subject(self):
        return self.cleaned_data["subject"].strip()

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 10:
            raise forms.ValidationError("내용은 10자 이상 입력해 주세요.")
        if len(message) > 3000:
            raise forms.ValidationError("내용은 3000자 이하로 입력해 주세요.")
        return message
