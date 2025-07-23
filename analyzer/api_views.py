from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import FlightData, Route, MarketDemand, Insight
from .serializers import FlightDataSerializer, RouteSerializer, MarketDemandSerializer, InsightSerializer
from .scraper import FlightScraper
from .ai_processor import AIProcessor

class FlightDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FlightData.objects.all().order_by('-scraped_at')
    serializer_class = FlightDataSerializer

class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

class MarketDemandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketDemand.objects.all().order_by('-date')
    serializer_class = MarketDemandSerializer

class InsightViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Insight.objects.all().order_by('-created_at')
    serializer_class = InsightSerializer

@api_view(['POST'])
def scrape_data_api(request):
    """API endpoint to trigger data scraping"""
    try:
        scraper = FlightScraper()
        result = scraper.scrape_amadeus_data()
        return Response({
            'success': True,
            'message': f"Successfully scraped {result.get('routes_analyzed', 0)} routes and {result.get('market_data_added', 0)} market records",
            'data': result
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def generate_insights_api(request):
    """API endpoint to generate AI insights"""
    try:
        ai_processor = AIProcessor()
        insights = ai_processor.generate_insights()
        return Response({
            'success': True,
            'message': f"Generated {len(insights)} insights",
            'insights': insights
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)