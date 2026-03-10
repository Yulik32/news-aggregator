from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        next_page='news:index'
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='news:index'
    ), name='logout'),
    
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
]