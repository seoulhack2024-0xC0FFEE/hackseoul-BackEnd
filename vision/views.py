# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Post, Location
from .serializers import PostSerializer, LocationSerializer
import openai
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Custom create method to analyze image and update location statistics.
        """
        post = serializer.save(user=self.request.user)
        cleanliness_score = self.analyze_image(post.image)
        post.cleanliness_score = cleanliness_score
        post.save()
        self.update_location_stats(post.location, cleanliness_score)

    @staticmethod
    def analyze_image(image):
        """
        Analyze the uploaded image using OpenAI's vision model to determine cleanliness.
        """
        import base64
        image_base64 = base64.b64encode(image.read()).decode('utf-8')
        
        openai.api_key = settings.OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "분석해주세요: 이 이미지의 자연환경이 청결한가요? 쓰레기가 보이나요? 1부터 10까지의 척도로 청결도를 평가해주세요."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ]
        )
        
        analysis = response.choices[0].message.content
        cleanliness_score = float(analysis.split('척도:')[-1].strip().split('/')[0])
        
        return cleanliness_score

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