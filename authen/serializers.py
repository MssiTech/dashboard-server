from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

CustomUser = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Username or email")
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login = attrs["username"]
        password = attrs["password"]

        user = CustomUser.objects.filter(username__iexact=login).first()
        if user is None:
            user = CustomUser.objects.filter(email__iexact=login).first()

        if user is None or not user.check_password(password):
            raise serializers.ValidationError(
                {"error": "Bunday foydalanuvchi mavjud emas! Foydalanuvchi nomi yoki parol noto‘g‘ri."}
            )

        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'groups']