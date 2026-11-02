from rest_framework import serializers


class BranchReceptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    branch = serializers.CharField()
    count = serializers.IntegerField()
