from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Budget, Category, Expense


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('That email is already registered.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'role', 'date_joined']

    def get_role(self, obj):
        return 'admin' if obj.is_staff else 'user'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

    def validate_name(self, value):
        return value.strip()


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'amount', 'month', 'year']
        read_only_fields = ['month', 'year']

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Budget cannot be negative.')
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'category', 'category_name', 'date',
            'payment_method', 'notes', 'created_at', 'user', 'username',
        ]
        read_only_fields = ['user', 'created_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else 'Uncategorized'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be more than 0.')
        return value