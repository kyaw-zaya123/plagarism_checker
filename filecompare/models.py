from django.db import models
from django.contrib.auth.models import User
import hashlib

class File(models.Model):
    """Model to store uploaded files."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, db_index=True)
    content = models.TextField(blank=True, null=True)
    content_hash = models.CharField(max_length=64, db_index=True, null=True)
    file_size = models.IntegerField(default=0)
    file_type = models.CharField(max_length=10, db_index=True, default='txt')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'filename']),  # Composite index for user's files
            models.Index(fields=['uploaded_at']),  # For sorting by date
            models.Index(fields=['content_hash']),  # For quick duplicate detection
            models.Index(fields=['user', 'file_type']),  # For filtering by user and file type
        ]

    def calculate_hash(self):
        """Calculate and set the content hash if content exists."""
        if self.content:
            self.content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def save(self, *args, **kwargs):
        """Override save to set content hash and file size."""
        if self.content and not self.content_hash:
            self.calculate_hash()
            
        if self.content:
            self.file_size = len(self.content.encode('utf-8'))
            
        if self.filename:
            ext = self.filename.rsplit('.', 1)[-1].lower() if '.' in self.filename else 'txt'
            self.file_type = ext[:10]  # Limit to 10 chars as defined in the model
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} - uploaded by {self.user.username}"


class FileRelation(models.Model):
    """Model to track relationships between files, e.g., duplicates."""
    RELATION_TYPES = [
        ('duplicate', 'Duplicate'),
        ('revision', 'Revision'),
        ('related', 'Related')
    ]
    
    source_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='source_relations')
    target_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='target_relations')
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('source_file', 'target_file', 'relation_type')
        indexes = [
            models.Index(fields=['relation_type']),
            models.Index(fields=['source_file', 'relation_type']),
        ]
        
    def __str__(self):
        return f"{self.source_file.filename} is {self.relation_type} of {self.target_file.filename}"


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
    tfidf_similarity = models.FloatField(default=0.0)
    semantic_similarity = models.FloatField(default=0.0)
    similarity_category = models.CharField(
        max_length=10,
        choices=SIMILARITY_CHOICES,
        default='low'
    )
    highlighted_content1 = models.TextField()
    highlighted_content2 = models.TextField()
    # Compressed results storage - optional but recommended for large comparisons
    compressed_results = models.TextField(blank=True, null=True)
    compared_at = models.DateTimeField(auto_now_add=True, db_index=True)
    comparison_name = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    # For caching purposes - helps track if comparison needs to be recalculated
    last_modified = models.DateTimeField(auto_now=True)

    duration = models.FloatField(default=0.0, help_text="Duration of comparison in seconds")

    class Meta:
        ordering = ['-compared_at']
        indexes = [
            models.Index(fields=['user']),  # Index user for faster queries
            models.Index(fields=['compared_at']),  # Faster sorting by date
            models.Index(fields=['similarity']),  # For filtering by similarity
            models.Index(fields=['file1', 'file2']),  # For finding specific comparisons
            models.Index(fields=['user', 'similarity']),  # For filtering user's comparisons by similarity
        ]  

    @property
    def similarity_category(self):
        """Dynamically set similarity category based on the similarity score."""
        if self.similarity <= 30:
            return 'low'
        elif self.similarity <= 60:  # Adjusted from 50 to 60 for better categorization
            return 'medium'
        else:
            return 'high'
        
        # Новые поля для хранения информации о строках
    no_match_lines_count = models.IntegerField(default=0)
    partial_match_lines_count = models.IntegerField(default=0)
    full_match_lines_count = models.IntegerField(default=0)
    total_lines_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        """Dynamically set comparison_name if not provided."""
        if not self.comparison_name:
            self.comparison_name = f"{self.file1.filename} vs {self.file2.filename}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comparison: {self.file1.filename} vs {self.file2.filename} - {self.similarity}%"


class ComparisonCache(models.Model):
    """Model to store cached comparison results for faster retrieval."""
    comparison = models.OneToOneField(Comparison, on_delete=models.CASCADE, related_name='cache')
    cache_key = models.CharField(max_length=100, unique=True, db_index=True)
    cache_expiry = models.DateTimeField()
    is_valid = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['is_valid']),
            models.Index(fields=['cache_expiry']),
        ]
        
    def __str__(self):
        return f"Cache for comparison {self.comparison_id}"