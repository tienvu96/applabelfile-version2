from django.urls import path
from .views import UploadView, delete_photo, delete_file
from . import views


app_name = "website"

urlpatterns = [
    path("", UploadView.as_view(), name="index"),
    path("delete-photo/<int:pk>/", delete_photo, name="photo-delete"),
    path("delete-file/<int:pk>/", delete_file, name="file-delete"),
    path('scan/<int:file_id>/', views.check_file_compliance, name='scan-file'),  # URL for scanning
    path('label/<int:file_id>/', views.label_file_by_rules, name='label-file'),  # URL for labeling
    path('download/<int:file_id>/', views.download_file_all, name='download-file'),  # URL for downloading
    path('author/', views.author, name='author'),
    path('introduce/', views.introduce, name='introduce'),
    path('rule/', views.rule, name='rule'),
    path('edit-label/<int:file_id>/<str:label_type>/', views.edit_label, name='edit_label'),


]
