from .models import Question, Answer, User, Bookmark
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets
from rest_framework.generics import (
    get_object_or_404,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status, permissions, filters
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser.conf import settings

from .serializers import (
    QuestionSerializer,
    QuestionWritableSerializer,
    AnswerSerializer,
    AnswerWritableSerializer,
    AnswerDetailSerializer,
    UserSerializer,
    UserCreateSerializer,
    BookmarkListSerializer,
    UserProfileSerializer,
)
from .custom_permissions import IsAuthorOrReadOnly


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Handle retrieve, create, edit, and destroy for questions.
    Allow full-text search on title, body, and tags via ?search=term.
    """

    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["@title", "@body", "@tags__name"]
    permission_classes = [IsAuthorOrReadOnly]

    def get_serializer_class(self):
        serializer_class_by_action = {
            "create": QuestionWritableSerializer,
            "list": QuestionSerializer,
            "retrieve": QuestionSerializer,
            "update": QuestionWritableSerializer,
            "partial_update": QuestionWritableSerializer,
            "destroy": QuestionWritableSerializer,
        }

        try:
            return serializer_class_by_action[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    @action(detail=False, methods=["get"])
    def me(self, request):
        if self.request.user.is_anonymous:
            content = {"reason": "You are not logged in"}
            return Response(content, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(
            request.user.questions.all(), many=True)
        return Response(serializer.data)


class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs.get("question_id")
        question = get_object_or_404(Question, pk=question_id)
        return Answer.objects.filter(question=question)

    def get_serializer_class(self):
        serializer_class_by_action = {
            "create": AnswerWritableSerializer,
            "list": AnswerSerializer,
            "retrieve": AnswerSerializer,
            "update": AnswerWritableSerializer,
            "partial_update": AnswerWritableSerializer,
            "destroy": AnswerWritableSerializer,
        }

        try:
            return serializer_class_by_action[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    def perform_create(self, serializer):
        question = get_object_or_404(Question, pk=self.kwargs["question_id"])
        serializer.save(question=question)


class AnswerListView(ListAPIView):
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Answer.objects.filter(author=self.request.user)


class AnswerDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerDetailSerializer
    permissions_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(author=self.request.user)


class AnswerAcceptView(UpdateAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer

    def update(self, request, *args, **kwargs):
        answer = self.get_object()
        accepted_value = request.data.get("accepted", None)
        if accepted_value is not None:
            answer.accepted = accepted_value
            answer.save()
        return Response(self.get_serializer(answer).data)

    def get_object(self):
        answer = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

        if self.request.user != answer.question.author:
            raise PermissionDenied(
                detail="Only the queston author can mark this answer as accepted."
            )
        return answer


class BookmarkListCreateView(ListCreateAPIView):
    serializer_class = BookmarkListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)


class ProfileDetailView(RetrieveAPIView):
    """
    Handle GET for user profiles.
    """

    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = "username"
