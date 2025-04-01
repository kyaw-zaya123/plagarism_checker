from django.db import models
from django.contrib.auth.models import User

class File(models.Model):
    """Model to store uploaded files."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, db_index=True)
    content = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} - uploaded by {self.user.username}"


class Comparison(models.Model):
    """Model to store file comparison results."""
    SIMILARITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file1 = models.ForeignKey(File, on_delete=models.CASCADE, related_name='comparison_file1')
    file2 = models.ForeignKey(File, on_delete=models.CASCADE, related_name='comparison_file2')
    similarity = models.FloatField()
    similarity_category = models.CharField(
        max_length=10,
        choices=SIMILARITY_CHOICES,
        default='low'
    )
    highlighted_content1 = models.TextField()
    highlighted_content2 = models.TextField()
    compared_at = models.DateTimeField(auto_now_add=True, db_index=True)
    comparison_name = models.CharField(max_length=200, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-compared_at']
        indexes = [
            models.Index(fields=['user']),  # Index user for faster queries
            models.Index(fields=['compared_at']),  # Faster sorting by date
        ]  

    @property
    def similarity_category(self):
        """Dynamically set similarity category based on the similarity score."""
        if self.similarity <= 30:
            return 'low'
        elif self.similarity <= 50:
            return 'medium'
        else:
            return 'high'

    def save(self, *args, **kwargs):
        """Dynamically set comparison_name if not provided."""
        if not self.comparison_name:
            self.comparison_name = f"{self.file1.filename} vs {self.file2.filename}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comparison: {self.file1.filename} vs {self.file2.filename} - {self.similarity}%"
