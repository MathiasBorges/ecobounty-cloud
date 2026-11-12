"""Views package."""
from app.views.camera_view import CameraView
from app.views.home_view import HomeView
from app.views.login_view import LoginView
from app.views.mission_view import MissionView
from app.views.profile_view import ProfileView
from app.views.reward_view import RewardView
from app.views.route_view import RouteView
from app.views.splash_view import SplashView

__all__ = [
    "SplashView",
    "LoginView",
    "HomeView",
    "MissionView",
    "RouteView",
    "CameraView",
    "RewardView",
    "ProfileView",
]
