from django import forms
import os

class FileUploadForm(forms.Form):
    """Form for uploading multiple files for comparison"""
    files = forms.FileField(
        widget=forms.SelectMultiple(attrs={'multiple': True}),
        help_text="Выберите несколько файлов для сравнения (PDF, DOCX, TXT поддерживаются",
        required=True
    )
    comparison_name = forms.CharField(max_length=200, required=True)

    def clean_files(self):
        """Validate uploaded files"""
        files = self.cleaned_data.get('files', [])

        if not files:
            raise forms.ValidationError("Пожалуйста, выберите хотя бы один файл для загрузки.")

        if len(files) > 10:
            raise forms.ValidationError("Максимум 10 файлов за один раз.")
        
        allowed_extensions = ['.pdf', '.docx', '.txt', '.doc']
        for file in files:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(f"Недопустимый тип файла: {file.name}. "
                                            f"Разрешенные типы: {', '.join(allowed_extensions)}")

            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(f"File {file.name} слишком большой. Максимум 10MB.")
        
        return files


from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add classes to form fields
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control input-with-icon'