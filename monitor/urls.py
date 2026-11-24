from django.urls import path
from monitor.ambulator.views import (
    DoctorsListAPIView,
    DoctorMonitoringAPIView,
    GetPatientDoctorAPIView,
    MonitoringListAPIView,
    PatientDoctorsAPIView,
)
from monitor.ambulator_doctor.views import (
    AmbulatorDoctorBottomAPIView,
    AmbulatorDoctorListAPIView,
    AmbulatorDoctorTopAPIView,
    AmbulatorReceptionListAPIView,
    AmbulatorReceptionSummaryAPIView,
    AmbulatorRetsepListAPIView,
)
from monitor.branch_monitor.views import BranchReceptionListAPIView
from monitor.district_monitor.views import (
    DistrictMonitoringListAPIView,
    DistrictPatientDetailAPIView,
    DistrictPatientsAPIView,
    DistrictStatsAPIView,
)
from monitor.month_monitor.views import (
    MonthMonitoringDetailAPIView,
    MonthMonitoringListAPIView,
    StasionaryBranchMonitoringListAPIView,
    StasionaryDoctorMonitoringListAPIView,
    StasionaryDoctorPatientsAPIView,
)
from monitor.employe.views import EmployeeListAPIView, EmployeDetailAPIView, BranchListAPIView


urlpatterns = [
    path('doctors/', DoctorsListAPIView.as_view(), name='doctors-list'),
    path('doctors/<int:doctor_id>/', DoctorMonitoringAPIView.as_view(), name='doctor-monitoring'),
    path('appointments/', GetPatientDoctorAPIView.as_view(), name='polyclinic-appointments'),
    path('patient-doctors/', PatientDoctorsAPIView.as_view(), name='patient-doctors'),
    path('', MonitoringListAPIView.as_view(), name='monitoring-list'),
    path('month/', MonthMonitoringListAPIView.as_view(), name='month-monitoring-list'),
    path('districts/', DistrictMonitoringListAPIView.as_view(), name='district-monitoring'),
    path('districts/patients/', DistrictPatientsAPIView.as_view(), name='district-patients'),
    path('districts/patients/<int:patient_id>/', DistrictPatientDetailAPIView.as_view(), name='district-patient-detail'),
    path('districts/stats/', DistrictStatsAPIView.as_view(), name='district-stats'),
    path('branches/', BranchReceptionListAPIView.as_view(), name='branch-receptions'),
    path('month/branches/', StasionaryBranchMonitoringListAPIView.as_view(), name='stasionary-branch-monitoring'),
    path('month/doctors/', StasionaryDoctorMonitoringListAPIView.as_view(), name='stasionary-doctor-monitoring'),
    path('month/doctors/<int:doctor_id>/', StasionaryDoctorPatientsAPIView.as_view(), name='stasionary-doctor-patients'),
    path('month/<int:doctor_id>/', MonthMonitoringDetailAPIView.as_view(), name='month-monitoring-detail'),

    path('ambulator-doctors/', AmbulatorDoctorListAPIView.as_view(), name='ambulator-doctors'),
    path('ambulator-doctors/receptions/', AmbulatorReceptionListAPIView.as_view(), name='ambulator-receptions'),
    path('ambulator-doctors/receptions/summary/', AmbulatorReceptionSummaryAPIView.as_view(), name='ambulator-receptions-summary'),
    path('ambulator-doctors/retseps/', AmbulatorRetsepListAPIView.as_view(), name='ambulator-retseps'),
    path('ambulator-doctors/top/', AmbulatorDoctorTopAPIView.as_view(), name='ambulator-doctors-top'),
    path('ambulator-doctors/bottom/', AmbulatorDoctorBottomAPIView.as_view(), name='ambulator-doctors-bottom'),
    path('employees/', EmployeeListAPIView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeDetailAPIView.as_view(), name='employee-detail'),
    path('employees/branches/', BranchListAPIView.as_view(), name='branch-list'),
]