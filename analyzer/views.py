from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta
import json
from .models import FlightData, Route, MarketDemand, Insight, Airport, Airline
from .scraper import FlightScraper
from .data_processor import DataProcessor

def dashboard(request):
    """Main dashboard view"""
    # Get recent flight data
    recent_flights = FlightData.objects.select_related('route__origin', 'route__destination', 'route__airline').order_by('-scraped_at')[:10]
    
    # Get popular routes
    popular_routes = Route.objects.annotate(
        flight_count=Count('flightdata')
    ).filter(flight_count__gt=0).order_by('-flight_count')[:5]
    
    # Get recent insights
    recent_insights = Insight.objects.order_by('-created_at')[:5]
    
    # Calculate basic stats
    total_routes = Route.objects.count()
    total_flights = FlightData.objects.count()
    avg_price = FlightData.objects.aggregate(avg_price=Avg('price'))['avg_price'] or 0
    
    context = {
        'recent_flights': recent_flights,
        'popular_routes': popular_routes,
        'recent_insights': recent_insights,
        'total_routes': total_routes,
        'total_flights': total_flights,
        'avg_price': round(avg_price, 2) if avg_price else 0,
    }
    
    return render(request, 'analyzer/dashboard.html', context)

def routes_analysis(request):
    """Routes analysis view"""
    routes = Route.objects.select_related('origin', 'destination', 'airline').annotate(
        avg_price=Avg('flightdata__price'),
        flight_count=Count('flightdata')
    ).filter(flight_count__gt=0)
    
    # Filter by origin if provided
    origin_filter = request.GET.get('origin')
    if origin_filter:
        routes = routes.filter(origin__iata_code=origin_filter)
    
    # Filter by destination if provided
    destination_filter = request.GET.get('destination')
    if destination_filter:
        routes = routes.filter(destination__iata_code=destination_filter)
    
    # Get all airports for filter dropdowns
    airports = Airport.objects.all().order_by('iata_code')
    
    context = {
        'routes': routes,
        'airports': airports,
        'origin_filter': origin_filter,
        'destination_filter': destination_filter,
    }
    
    return render(request, 'analyzer/routes_analysis.html', context)

def pricing_trends(request):
    """Pricing trends analysis view"""
    # FIXED: Look for flight data in both past and future to handle sample data
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    future_end_date = end_date + timedelta(days=30)
    
    # Get pricing data from past 30 days AND next 30 days
    pricing_data = FlightData.objects.filter(
        Q(departure_time__date__range=[start_date, end_date]) |
        Q(departure_time__date__range=[end_date, future_end_date])
    ).select_related('route__origin', 'route__destination')
    
    # Group by route and date for trend analysis
    trends = {}
    for flight in pricing_data:
        route_key = f"{flight.route.origin.iata_code}-{flight.route.destination.iata_code}"
        date_key = flight.departure_time.date().isoformat()
        
        if route_key not in trends:
            trends[route_key] = {}
        
        if date_key not in trends[route_key]:
            trends[route_key][date_key] = []
        
        trends[route_key][date_key].append(float(flight.price))
    
    # Calculate average prices per day for each route
    trend_data = {}
    for route, dates in trends.items():
        trend_data[route] = {}
        for date, prices in dates.items():
            trend_data[route][date] = sum(prices) / len(prices)
    
    # Debug info
    print(f"Pricing data query returned {pricing_data.count()} flights")
    print(f"Trend data contains {len(trend_data)} routes")
    
    context = {
        'trend_data': json.dumps(trend_data),
        'start_date': start_date,
        'end_date': end_date,
        'data_count': pricing_data.count(),
    }
    
    return render(request, 'analyzer/pricing_trends.html', context)

def demand_analysis(request):
    """Market demand analysis view"""
    demand_data = MarketDemand.objects.select_related('route__origin', 'route__destination').order_by('-date')[:50]
    
    # Group by demand level
    demand_summary = MarketDemand.objects.values('demand_level').annotate(
        count=Count('id'),
        avg_price=Avg('average_price')
    )
    
    context = {
        'demand_data': demand_data,
        'demand_summary': demand_summary,
    }
    
    return render(request, 'analyzer/demand_analysis.html', context)

def insights(request):
    """AI-generated insights view"""
    insights = Insight.objects.order_by('-created_at')
    
    # Group insights by type
    insights_by_type = {}
    for insight in insights:
        if insight.insight_type not in insights_by_type:
            insights_by_type[insight.insight_type] = []
        insights_by_type[insight.insight_type].append(insight)
    
    context = {
        'insights': insights,
        'insights_by_type': insights_by_type,
    }
    
    return render(request, 'analyzer/insights.html', context)

def manual_scrape(request):
    """Manual data scraping trigger"""
    if request.method == 'POST':
        try:
            scraper = FlightScraper()
            result = scraper.scrape_amadeus_data()
            
            if result['success']:
                if result.get('routes_analyzed', 0) > 0:
                    messages.success(request, f"Successfully scraped real Amadeus data: {result['routes_analyzed']} routes analyzed, {result['market_data_added']} market records added")
                else:
                    messages.success(request, f"Successfully generated {result.get('flights_added', 0)} sample flight records")
            else:
                messages.error(request, f"Scraping failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            messages.error(request, f"Scraping failed: {str(e)}")
    
    return render(request, 'analyzer/manual_scrape.html')