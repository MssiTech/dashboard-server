from rest_framework import serializers

from monitor.ambulator.serializers import DoctorsSerializer


class BranchMonitoringSerializer(serializers.Serializer):
    branch = serializers.CharField()
    appointment_count = serializers.IntegerField()
    rezident_count = serializers.IntegerField()
    non_rezident_count = serializers.IntegerField()
    simple_count = serializers.IntegerField()
    examination_count = serializers.IntegerField()
    diagnosis_count = serializers.IntegerField()
    analysis_count = serializers.IntegerField()
    diagnostika_count = serializers.IntegerField()


class StationaryDoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    doctor = serializers.CharField()
    branch = serializers.CharField()
    appointment_count = serializers.IntegerField()
    rezident_count = serializers.IntegerField()
    non_rezident_count = serializers.IntegerField()
    simple_count = serializers.IntegerField()
    examination_count = serializers.IntegerField()
    diagnosis_count = serializers.IntegerField()
    analysis_count = serializers.IntegerField()
    diagnostika_count = serializers.IntegerField()


class MonthMonitoringSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    doctor = DoctorsSerializer()
    appointment_count = serializers.IntegerField()
    current_view_count = serializers.IntegerField()
    examination_count = serializers.IntegerField()
    diagnosis_count = serializers.IntegerField()
    analysis_count = serializers.IntegerField()
    diagnostika_count = serializers.IntegerField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
