from rest_framework import serializers


class AmbulatorDoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dmed_id = serializers.CharField()
    full_name = serializers.CharField()
    branch = serializers.CharField()
    bid = serializers.CharField()
    daily_limit = serializers.CharField()
    monthly_limit = serializers.CharField()
    daily_count = serializers.IntegerField()
    daily_percent = serializers.FloatField()
    monthly_count = serializers.IntegerField()
    monthly_percent = serializers.FloatField()


class AmbulatorDoctorTopSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dmed_id = serializers.CharField()
    full_name = serializers.CharField()
    branch = serializers.CharField()
    bid = serializers.CharField()
    daily_limit = serializers.CharField()
    daily_count = serializers.IntegerField()
    daily_percent = serializers.FloatField()
    monthly_count = serializers.IntegerField()
    monthly_percent = serializers.FloatField()
