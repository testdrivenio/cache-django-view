from django.urls import path

from .views import ApiCalls

urlpatterns = [
    path('', ApiCalls.as_view(), name='api_results'),
]
