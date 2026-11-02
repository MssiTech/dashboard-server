from django.urls import path

from month_monitor.views import (
    BranchPatientsAPIView,
    BranchSummaryAPIView,
    DoctorPatientsAPIView,
    ExaminationSummaryAPIView,
)

urlpatterns = [
    path("examinations/", ExaminationSummaryAPIView.as_view(), name="month-examinations"),
    path("branches/", BranchSummaryAPIView.as_view(), name="month-branches"),
    path("branches/<int:doctor_id>/", BranchPatientsAPIView.as_view(), name="month-branch-patients"),
    path("examinations/<int:doctor_id>/", DoctorPatientsAPIView.as_view(), name="month-doctor-patients"),
]
