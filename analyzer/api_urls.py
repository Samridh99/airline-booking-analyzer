from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'flights', api_views.FlightDataViewSet)
router.register(r'routes', api_views.RouteViewSet)
router.register(r'demand', api_views.MarketDemandViewSet)
router.register(r'insights', api_views.InsightViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('scrape-data/', api_views.scrape_data_api, name='scrape_data_api'),
    path('generate-insights/', api_views.generate_insights_api, name='generate_insights_api'),
]