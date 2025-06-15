from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import delete_comparison

urlpatterns = [
    path('', views.home, name='home'),
    path('history/', views.comparison_history, name='comparison_history'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='filecompare/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('upload/', views.upload_files, name='upload_files'),
    path('comparison/<int:comparison_id>/', views.view_comparison, name='view_comparison'),
    path('search/', views.search_comparisons, name='search_comparisons'),
    path('delete_comparison/<int:comparison_id>/', delete_comparison, name='delete_comparison'),
    path('generate_pdf/<int:comparison_id>/', views.generate_pdf, name='generate_pdf'),

]