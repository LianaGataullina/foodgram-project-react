from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from recipes.models import Favorite, Ingredient, IngredientRecipe, Recipe, Tag
from users.models import Subscribe, User


def get_is_subscribed(self, obj):
    user = self.context['request'].user
    if user.is_anonymous:
        return False
    return Subscribe.objects.filter(
        user=user,
        author=obj
    ).exists()


def add_ingredients(recipe, ingredients):
    ingredients_batch = []
    for ingredient in ingredients:
        amount = ingredient.get('amount')
        ingredient_id = get_object_or_404(Ingredient, id=ingredient.get('id'))
        ingredients_batch.append(IngredientRecipe(recipe=recipe, ingredient=ingredient_id, amount=amount))
    IngredientRecipe.objects.bulk_create(ingredients_batch, len(ingredients_batch))
    recipe.save()


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'password')


class CustomUserSerializer(UserSerializer):
    get_is_subscribed = get_is_subscribed
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', )


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SubscriptionsRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeSerializer(serializers.ModelSerializer):
    get_is_subscribed = get_is_subscribed
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', )

    def get_recipes(self, obj):
        limit = self.context['request'].query_params.get('recipes_limit')
        if limit is None:
            recipes = obj.recipes.all()
        else:
            recipes = obj.recipes.all()[:int(limit)]
        return SubscriptionsRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time', )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug', )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', )


class IngredientRecipeListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount', )


class IngredientRecipeCreateSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField(write_only=True)
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'id',
            'amount'
        ]


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientRecipeListSerializer(
        many=True,
        source='ingredient_recipe'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Recipe.objects.filter(
            shopping_cart__user=user,
            id=obj.id
        ).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = IngredientRecipeCreateSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time', 'author')

    def validate_tags(self, tags):
        if not tags:
            raise ValidationError('В рецепте не заполнены теги!')
        for tag in tags:
            if tags.count(tag) > 1:
                raise ValidationError('Повтор тега - {tag}!')
        return tags

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise ValidationError('Нужно выбрать минимум 1 ингредиент!')
        for ingredient in ingredients:
            if int(ingredient['amount']) <= 0:
                raise ValidationError('Количество должно быть положительным!')
            if ingredients.count(ingredient) > 1:
                raise ValidationError('Повтор ингредиента - {ingredient}!')
        return ingredients

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        add_ingredients(recipe, ingredients)
        return recipe

    def update(self, recipe, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe.tags.clear()
        recipe.ingredients.clear()
        super().update(recipe, validated_data)
        for tag in tags_data:
            tag_id = tag.id
            tag_object = get_object_or_404(Tag, id=tag_id)
            recipe.tags.add(tag_object)
        add_ingredients(recipe, ingredients)
        return recipe

    def to_representation(self, instance):
        serializer = RecipeListSerializer(
            instance,
            context=self.context
        )
        return serializer.data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time', )