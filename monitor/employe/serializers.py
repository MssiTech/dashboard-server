from rest_framework import serializers

from monitor.models import Doctors, Branches, DoctorMonthPlan


class DoctorMonthPlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = DoctorMonthPlan
        fields = ['id', 'year', 'month', 'bid', 'daily_limit', 'monthly_limit']
 

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branches
        fields = ['id', 'name']


class EmployeeSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)
    month_plans = DoctorMonthPlanSerializer(read_only=True, many=True)

    class Meta:
        model = Doctors
        fields = ['id', 'full_name', 'branch', 'specialization', 'polyclinic', 'month_plans']


class EmployeUpdateSerializer(serializers.ModelSerializer):
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branches.objects.all(),
        allow_null=True,
        required=False,
    )
    year = serializers.IntegerField(required=False, write_only=True)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12, write_only=True)

    class Meta:
        model = Doctors
        fields = [
            'full_name',
            'branch',
            'specialization',
            'polyclinic',
            'bid',
            'daily_limit',
            'monthly_limit',
            'time_count_patient',
            'work_normal',
            'year',
            'month',
        ]

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.branch = validated_data.get('branch', instance.branch)
        instance.specialization = validated_data.get('specialization', instance.specialization)
        instance.polyclinic = validated_data.get('polyclinic', instance.polyclinic)
        instance.save()
        return instance
