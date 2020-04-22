from django.urls import path
from django.views.decorators.cache import cache_page

from .views import ApiCalls

urlpatterns = [
    path('', cache_page(60 * 15)(ApiCalls.as_view()), name='api_results'),
    path('uncached/', ApiCalls.as_view(), name='api_results_uncached')
]
