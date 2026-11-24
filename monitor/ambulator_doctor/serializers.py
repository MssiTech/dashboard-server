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


class AmbulatorReceptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dmed_id = serializers.CharField()
    full_name = serializers.CharField()
    branch = serializers.CharField()
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    completed = serializers.IntegerField()


class AmbulatorRetsepSerializer(serializers.Serializer):
    count = serializers.IntegerField()


class AmbulatorReceptionSummarySerializer(serializers.Serializer):
    umumiy_qabullar = serializers.IntegerField()
    active = serializers.IntegerField()
    bajarildi = serializers.IntegerField()
    diagnostika = serializers.IntegerField()
    tahlil = serializers.IntegerField()


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
