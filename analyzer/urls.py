from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('routes/', views.routes_analysis, name='routes_analysis'),
    path('pricing/', views.pricing_trends, name='pricing_trends'),
    path('demand/', views.demand_analysis, name='demand_analysis'),
    path('insights/', views.insights, name='insights'),
    path('scrape/', views.manual_scrape, name='manual_scrape'),
]