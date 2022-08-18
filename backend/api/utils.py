from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Ingredient, IngredientRecipe, Recipe


def add_ingredients(recipe, ingredients):
    ingredients_batch = []
    for ingredient in ingredients:
        amount = ingredient.get('amount')
        ingredient_id = get_object_or_404(Ingredient, id=ingredient.get('id'))
        ingredients_batch.append(IngredientRecipe(
            recipe=recipe, ingredient=ingredient_id, amount=amount))
    IngredientRecipe.objects.bulk_create(
        ingredients_batch, len(ingredients_batch))


def add_to_favorite_or_shopping_cart(
        self, request, object_class, serializer_class, pk=None):
    user = self.request.user
    recipe = get_object_or_404(Recipe, pk=pk)
    object_class_exists = object_class.objects.filter(
        user=user, recipe=recipe
    ).exists()
    if request.method == 'POST':
        if not object_class_exists:
            instance = object_class.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(instance.recipe)
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
    elif request.method == 'DELETE':
        if not object_class_exists:
            data = {'errors': 'Такого рецепта нет'}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        object_class.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
