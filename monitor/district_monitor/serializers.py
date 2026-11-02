from rest_framework import serializers


class DistrictMonitoringSerializer(serializers.Serializer):
    district = serializers.CharField()
    count = serializers.IntegerField()


class DistrictCountSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()


class DistrictStatsSerializer(serializers.Serializer):
    district = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    diseases = DistrictCountSerializer(many=True)
    branches = DistrictCountSerializer(many=True)


class DistrictPatientSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    neighborhood = serializers.CharField()
    polyclinic = serializers.CharField()
    branch = serializers.CharField()
    mkb_10_name = serializers.CharField()
    reception_date = serializers.CharField()
    doctor = serializers.CharField()


class DistrictPatientDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    patient = serializers.CharField()
    region = serializers.CharField()
    city = serializers.CharField()
    neighborhood = serializers.CharField()
    polyclinic = serializers.CharField()
    phone = serializers.CharField()
    birth_date = serializers.CharField()
    passport_series = serializers.CharField()
    inn = serializers.CharField()
    branch = serializers.CharField()
    reception_date = serializers.CharField()
    doctor = serializers.CharField()
    mkb_10_name = serializers.CharField()
