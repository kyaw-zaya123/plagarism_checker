from django import forms
import os

class FileUploadForm(forms.Form):
    """Form for uploading multiple files for comparison"""
    files = forms.FileField(
        widget=forms.SelectMultiple(attrs={'multiple': True}),
        help_text="Select multiple files to compare (PDF, DOCX, TXT supported)",
        required=True
    )
    comparison_name = forms.CharField(max_length=200, required=True)

    def clean_files(self):
        """Validate uploaded files"""
        files = self.cleaned_data.get('files', [])
        
        # Check if files are actually provided (in case no files are selected)
        if not files:
            raise forms.ValidationError("Please select at least one file to upload.")
        
        # Check maximum number of files
        if len(files) > 10:
            raise forms.ValidationError("You can upload a maximum of 10 files at once.")
        
        # Validate file types
        allowed_extensions = ['.pdf', '.docx', '.txt', '.doc']
        for file in files:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(f"Unsupported file type: {file.name}. "
                                            f"Allowed types are: {', '.join(allowed_extensions)}")
            
            # Optional: Check file size (e.g., max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(f"File {file.name} is too large. Max file size is 10MB.")
        
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