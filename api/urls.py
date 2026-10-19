from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path('auth/register/', views.register),
    path('auth/login/', TokenObtainPairView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('auth/me/', views.get_me),

    path('categories/', views.categories),
    path('categories/<int:pk>/', views.category_detail),

    path('expenses/', views.expenses),
    path('expenses/<int:pk>/', views.expense_detail),

    path('budget/', views.budget),
    path('dashboard/', views.dashboard),
    path('admin-dashboard/', views.admin_dashboard),
]