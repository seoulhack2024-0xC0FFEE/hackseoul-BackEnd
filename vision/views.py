# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Post, Location
from .serializers import PostSerializer, LocationSerializer
from openai import OpenAI
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import base64
from io import BytesIO
from PIL import Image
import json
from django.core.files.base import ContentFile

client = OpenAI(api_key=settings.OPENAI_API_KEY)

from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Post, Location
from .serializers import PostSerializer
from django.contrib.auth.models import User

class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing posts with environmental cleanliness analysis.
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    @swagger_auto_schema(
        operation_description="List all posts or create a new post with automatic cleanliness analysis.",
        responses={
            200: openapi.Response('Success', PostSerializer(many=True)),
            201: openapi.Response('Created', PostSerializer),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def list(self, request):
        """
        Retrieve a list of all posts.
        """
        return super().list(request)

    @swagger_auto_schema(
        operation_description="Create a new post with automatic image analysis for environmental cleanliness.",
        request_body=PostSerializer,
        responses={
            201: openapi.Response('Created', PostSerializer),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def create(self, request):
        """
        Create a new post with automatic cleanliness analysis of the uploaded image.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer,request)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer,request):
        """
        Custom create method to analyze image and update location statistics.
        """
        post = serializer.save(user=self.request.user)
        image_data = request.data.get('image')
        
        # Call the analyze_image function
        cleanliness_score = self.analyze_image(image_data)
        
        # Ensure only the cleanliness score (number) is saved
        post.cleanliness_score = cleanliness_score
        post.save()

        # Update location stats
        location_name = post.location

        # 만약 location_name에 해당하는 Location 객체가 없다면 생성하고, 있다면 가져오기
        location, created = Location.objects.get_or_create(
            name=location_name,
            defaults={
                'latitude': 0.0,  # post에서 latitude를 가져오도록 수정해야 합니다.
                'longitude': 0.0  # post에서 longitude를 가져오도록 수정해야 합니다.
            }
        )

        if not created:
            # Location 객체가 이미 있는 경우, 평균 청결도를 업데이트
            self.update_location_stats(location, cleanliness_score)
        else:
            # 만약 새로 생성된 경우, 청결도 점수를 설정
            location.average_cleanliness = cleanliness_score
            location.save()


    @staticmethod
    def analyze_image(image):
        """
        Analyze the uploaded image using OpenAI's vision model to determine cleanliness.
        """
        if 'base64,' in image:
            image = image.split('base64,')[1]
        
        print(image)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "분석해주세요: 이 이미지의 자연환경이 청결한가요? 쓰레기가 보이나요? 1부터 10까지의 척도로 청결도를 평가해주세요."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}
                    ]
                }
            ],
            functions=[
                {
                    "name": "get_cleanliness_report",
                    "description": "Provides a detailed report on the cleanliness of the environment in the image.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cleanliness_score": {
                                "type": "integer",
                                "description": "A score from 1 to 10 indicating the cleanliness of the environment."
                            },
                            "trash_present": {
                                "type": "boolean",
                                "description": "Indicates whether trash is present in the image."
                            },
                            "details": {
                                "type": "string",
                                "description": "Additional details about the cleanliness and any observed trash."
                            }
                        },
                        "required": ["cleanliness_score", "trash_present", "details"]
                    }
                }
            ],
            function_call={"name": "get_cleanliness_report"}
        )
        
        # cleanliness_report = response.choices[0].message['function_call']['arguments']
        if response.choices:
            function_call = response.choices[0].message.function_call
            if function_call and hasattr(function_call, 'arguments'):
                cleanliness_report = function_call.arguments  # Correct way to access
                print(cleanliness_report)  # Debugging

                # Parse the returned JSON-like string to a Python dictionary
                cleanliness_report_dict = json.loads(cleanliness_report)

                # Extract the cleanliness score
                cleanliness_score = cleanliness_report_dict['cleanliness_score']
                print(cleanliness_score)  # Debugging
                return cleanliness_score 
        # print(cleanliness_report)
        
        # return cleanliness_report
        return None

    @staticmethod
    def update_location_stats(location_name, cleanliness_score):
        """
        Update the average cleanliness score for a given location.
        """
        location, created = Location.objects.get_or_create(name=location_name)
        posts = Post.objects.filter(location=location_name)
        location.average_cleanliness = (location.average_cleanliness * (posts.count() - 1) + cleanliness_score) / posts.count()
        location.save()


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving location data and cleanliness statistics.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all locations with their average cleanliness scores.",
        responses={
            200: openapi.Response('Success', LocationSerializer(many=True)),
            401: "Unauthorized"
        }
    )
    def list(self, request):
        """
        Retrieve a list of all locations with their average cleanliness scores.
        """
        return super().list(request)

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific location including its average cleanliness score.",
        responses={
            200: openapi.Response('Success', LocationSerializer),
            404: "Not Found",
            401: "Unauthorized"
        }
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve details of a specific location including its average cleanliness score.
        """
        return super().retrieve(request, pk)

    @swagger_auto_schema(
        operation_description="Retrieve the top 5 cleanest locations based on average cleanliness scores.",
        responses={
            200: openapi.Response('Success', LocationSerializer(many=True)),
            401: "Unauthorized"
        }
    )
    @action(detail=False, methods=['get'])
    def top_cleanest(self, request):
        """
        Retrieve the top 5 cleanest locations based on average cleanliness scores.
        """
        locations = self.get_queryset().order_by('-average_cleanliness')[:5]
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)