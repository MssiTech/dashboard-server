from rest_framework import serializers

from monitor.models import Doctors, Monitoring


class DoctorsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Doctors
        fields = ['id', 'full_name']


class MonitoringSerializer(serializers.ModelSerializer):
    doctor = DoctorsSerializer(read_only=True)

    class Meta:
        model = Monitoring
        fields = [
            'id',
            'doctor',
            'appointment_count',
            'current_view_count',
            'examination_count',
            'diagnosis_count',
            'analysis_count',
            'diagnostika_count',
            'date',
        ]


class ExamItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField()


def patient_passport(patient):
    return {
        "region": patient.region or "",
        "city": patient.city or "",
        "neighborhood": patient.neighborhood or "",
        "polyclinic": patient.polyclinic or "",
        "phone": patient.phone or "",
        "birth_date": patient.birth_date.isoformat() if patient.birth_date else "",
        "passport_series": patient.passport_series or "",
        "inn": patient.inn or "",
    }


class PatientMonitoringSerializer(serializers.Serializer):
    def to_representation(self, patient):
        views = [item for item in patient.patient_current_view.all() if item.mkb_10_name]
        diagnosis = next(iter(patient.pattientcurrentdiagnosis_set.all()), None)
        diagnostics = {}
        laboratories = {}

        if diagnosis:
            self._collect(diagnostics, diagnosis.currentviewdiagnosis_set.all(), "diagnosis")
            self._collect(laboratories, diagnosis.currentviewlaboratory_set.all(), "laboratory")

        return {
            "patient_name": patient.patient or "",
            **patient_passport(patient),
            "examination": ", ".join(item.mkb_10_name for item in views),
            "diagnosis": diagnosis.mkb_10_name if diagnosis and diagnosis.mkb_10_name else "",
            "diagnostics": self._items(diagnostics),
            "laboratory": self._items(laboratories),
        }

    def _collect(self, found, rows, field_name):
        for row in rows:
            name = getattr(row, field_name) or ""
            found[name] = found.get(name, False) or bool(row.is_exists)

    def _items(self, found):
        return [
            {"name": name, "status": "bor" if exists else "yo'q"}
            for name, exists in found.items()
        ]
