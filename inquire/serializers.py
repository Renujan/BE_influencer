from rest_framework import serializers
from inquire.models import Inquiry

class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            'id',
            'inquiry_id',
            'name',
            'email',
            'phone',
            'role',
            'subject',
            'message',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'inquiry_id', 'created_at', 'updated_at']
