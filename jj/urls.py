from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('member/', views.member_overview, name='member_overview'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/edit/<int:session_id>/', views.edit_session, name='edit_session'),
    path('session/edit/', views.edit_session, name='edit_session'),  # For creating new sessions
    path('transcribe-audio/', views.transcribe_audio, name='transcribe_audio'),
    path('generate-response/', views.generate_response, name='generate_response'),
]
