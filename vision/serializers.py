from rest_framework import serializers
from .models import Post, Location
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
import base64
import uuid
import six
import imghdr

class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.
    """
    
    def to_internal_value(self, data):
        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if 'data:' in data and ';base64,' in data:
                # Break out the header from the base64 content
                header, data = data.split(';base64,')

            # Try to decode the file. 
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            # Generate file name:
            file_name = str(uuid.uuid4())[:12] # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension, )
            
            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        # Get the file extension using imghdr
        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Post
        fields = ['id', 'user', 'image', 'location', 'cleanliness_score', 'created_at']
        read_only_fields = ['cleanliness_score']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'average_cleanliness']