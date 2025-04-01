# serializers.py
from rest_framework import serializers
from .models import File, Comparison

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'filename', 'user', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']  # user should be read-only


class ComparisonSerializer(serializers.ModelSerializer):
    """Serializer for the Comparison model."""
    similarity_category = serializers.ReadOnlyField()  # To include the dynamically computed category

    class Meta:
        model = Comparison
        fields = [
            'id', 'user', 'file1', 'file2', 'compared_at', 'similarity_category', 
            'comparison_name', 'similarity'  # Added similarity to fields
        ]
        read_only_fields = ['id', 'compared_at']

    def validate(self, data):
        """Ensure that file1 and file2 are not the same."""
        if data['file1'] == data['file2']:
            raise serializers.ValidationError("Files cannot be compared to themselves.")
        
        # Provide a default value for similarity if not present
        if 'similarity' not in data:
            data['similarity'] = 0.0  # Default value
            
        return data
    