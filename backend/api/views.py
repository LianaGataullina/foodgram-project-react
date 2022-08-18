import csv

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .mixins import RetrieveListViewSet
from .permissions import IsAuthorAdminOrReadOnly
from .serializers import (CustomUserSerializer, FavoriteSerializer,
                          IngredientSerializer, PasswordSerializer,
                          RecipeCreateSerializer, RecipeListSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          TagSerializer)
from .utils import add_to_favorite_or_shopping_cart
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe, User


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    @action(detail=False,
            methods=['post'],
            permission_classes=(IsAuthenticated, ))
    def set_password(self, request, pk=None):
        user = self.request.user
        serializer = PasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated, ))
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(follower__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=['get', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def subscribe(self, request, id):
        user = self.request.user
        author = get_object_or_404(User, id=id)
        subscribe = Subscribe.objects.filter(user=user, author=author)
        if request.method == 'GET':
            if subscribe.exists():
                data = {
                    'errors': ('Вы подписаны на этого автора, '
                               'или пытаетесь подписаться на себя.')}
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
            Subscribe.objects.create(user=user, author=author)
            serializer = SubscribeSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not subscribe.exists():
                data = {'errors': 'Вы не подписаны на данного автора.'}
                return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
            subscribe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class TagsViewSet(RetrieveListViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny, )
    pagination_class = None


class IngredientsViewSet(RetrieveListViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter
    pagination_class = None


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeListSerializer
    permission_classes = (IsAuthorAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeListSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def favorite(self, request, pk=None):
        return add_to_favorite_or_shopping_cart(
            self, request, Favorite, FavoriteSerializer, pk)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated, ],
    )
    def shopping_cart(self, request, pk=None):
        return add_to_favorite_or_shopping_cart(
            self, request, ShoppingCart, ShoppingCartSerializer, pk)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated, ],
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок."""
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(ingredient_amount=Sum('amount')).values_list(
            'ingredient__name', 'ingredient__measurement_unit',
            'ingredient_amount')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = ('attachment;'
                                           'filename="Shoppingcart.csv"')
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        for item in list(ingredients):
            writer.writerow(item)
        return response
