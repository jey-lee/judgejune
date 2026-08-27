from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('landing', views.landing, name='landing'),
    path('profile', views.profile, name='profile'),
    path('profile/', views.profile, name='profile_slash'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('member/', views.member_overview, name='member_overview'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/edit/<int:session_id>/', views.edit_session, name='edit_session'),
    path('session/edit/', views.edit_session, name='edit_session'),  # For creating new sessions
    path('session/create/', views.create_session, name='create_session'),
    path('session/createnew/', views.create_new_session, name='create_new_session'),
    path('generate-response/', views.generate_response, name='generate_response'),
    path('session/delete/<int:session_id>/', views.delete_session, name='delete_session'),
    path('transcribe/', views.transcribe, name='transcribe'),
    path('sessiontoken/', views.sessiontoken_view, name='sessiontoken'),
    path('api/realtime_token/', views.realtime_token, name='realtime_token'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('support/', views.support_view, name='support'),
]
