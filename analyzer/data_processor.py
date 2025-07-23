import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min, Q
from .models import FlightData, Route, MarketDemand, Airport, Airline
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        pass
    
    def process_flight_data(self):
        """Process raw flight data and generate market demand insights"""
        try:
            # Get recent flight data
            recent_flights = FlightData.objects.filter(
                scraped_at__gte=timezone.now() - timedelta(days=30)
            ).select_related('route__origin', 'route__destination', 'route__airline')
            
            if not recent_flights.exists():
                logger.warning("No recent flight data to process")
                return {'processed': 0, 'insights_generated': 0}
            
            # Process data by route and date
            processed_count = 0
            insights_count = 0
            
            # Group flights by route and date
            route_date_groups = {}
            for flight in recent_flights:
                route_id = flight.route.id
                flight_date = flight.departure_time.date()
                
                key = (route_id, flight_date)
                if key not in route_date_groups:
                    route_date_groups[key] = []
                route_date_groups[key].append(flight)
            
            # Process each group
            for (route_id, flight_date), flights in route_date_groups.items():
                route = Route.objects.get(id=route_id)
                
                # Calculate metrics
                prices = [float(f.price) for f in flights]
                avg_price = sum(prices) / len(prices)
                search_volume = len(flights)  # Using flight count as proxy for search volume
                
                # Determine price trend (simplified)
                price_trend = self.calculate_price_trend(route, flight_date, avg_price)
                
                # Determine demand level
                demand_level = self.calculate_demand_level(search_volume, avg_price)
                
                # Create or update market demand record
                market_demand, created = MarketDemand.objects.update_or_create(
                    route=route,
                    date=flight_date,
                    defaults={
                        'search_volume': search_volume,
                        'average_price': round(avg_price, 2),
                        'price_trend': price_trend,
                        'demand_level': demand_level
                    }
                )
                
                if created:
                    processed_count += 1
            
            logger.info(f"Processed {processed_count} market demand records")
            return {'processed': processed_count, 'insights_generated': insights_count}
            
        except Exception as e:
            logger.error(f"Error processing flight data: {str(e)}")
            return {'processed': 0, 'insights_generated': 0, 'error': str(e)}
    
    def calculate_price_trend(self, route, current_date, current_price):
        """Calculate price trend for a route"""
        try:
            # Get historical data for the same route
            week_ago = current_date - timedelta(days=7)
            historical_data = MarketDemand.objects.filter(
                route=route,
                date__gte=week_ago,
                date__lt=current_date
            ).order_by('-date')
            
            if not historical_data.exists():
                return 'stable'
            
            # Compare with most recent historical price
            recent_price = float(historical_data.first().average_price)
            price_change = (current_price - recent_price) / recent_price
            
            if price_change > 0.1:  # 10% increase
                return 'increasing'
            elif price_change < -0.1:  # 10% decrease
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error calculating price trend: {str(e)}")
            return 'stable'
    
    def calculate_demand_level(self, search_volume, avg_price):
        """Calculate demand level based on search volume and pricing"""
        try:
            # Simple heuristic for demand level
            # This could be enhanced with more sophisticated algorithms
            
            if search_volume >= 20:
                return 'very_high'
            elif search_volume >= 10:
                return 'high'
            elif search_volume >= 5:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Error calculating demand level: {str(e)}")
            return 'medium'
    
    def get_route_analytics(self, route_id=None):
        """Get analytics for specific route or all routes"""
        try:
            query = FlightData.objects.select_related('route__origin', 'route__destination', 'route__airline')
            
            if route_id:
                query = query.filter(route_id=route_id)
            
            # Calculate key metrics
            analytics = {
                'total_flights': query.count(),
                'average_price': query.aggregate(avg_price=Avg('price'))['avg_price'] or 0,
                'price_range': {
                    'min': query.aggregate(min_price=Min('price'))['min_price'] or 0,
                    'max': query.aggregate(max_price=Max('price'))['max_price'] or 0
                },
                'popular_routes': self.get_popular_routes(query),
                'price_trends': self.get_price_trends(query),
                'demand_patterns': self.get_demand_patterns()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting route analytics: {str(e)}")
            return {}
    
    def get_popular_routes(self, queryset):
        """Get most popular routes from flight data"""
        try:
            route_counts = queryset.values(
                'route__origin__iata_code',
                'route__destination__iata_code',
                'route__origin__city',
                'route__destination__city'
            ).annotate(
                flight_count=Count('id'),
                avg_price=Avg('price')
            ).order_by('-flight_count')[:10]
            
            return list(route_counts)
            
        except Exception as e:
            logger.error(f"Error getting popular routes: {str(e)}")
            return []
    
    def get_price_trends(self, queryset):
        """Get price trends over time"""
        try:
            # Group by date and calculate daily averages
            daily_prices = queryset.extra(
                select={'day': 'date(departure_time)'}
            ).values('day').annotate(
                avg_price=Avg('price'),
                flight_count=Count('id')
            ).order_by('day')
            
            return list(daily_prices)
            
        except Exception as e:
            logger.error(f"Error getting price trends: {str(e)}")
            return []
    
    def get_demand_patterns(self):
        """Get demand patterns from market demand data"""
        try:
            demand_data = MarketDemand.objects.values('demand_level').annotate(
                count=Count('id'),
                avg_price=Avg('average_price'),
                avg_search_volume=Avg('search_volume')
            ).order_by('demand_level')
            
            return list(demand_data)
            
        except Exception as e:
            logger.error(f"Error getting demand patterns: {str(e)}")
            return []
    
    def export_data_to_csv(self, filename=None):
        """Export flight data to CSV for further analysis"""
        try:
            if not filename:
                filename = f"flight_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            flights = FlightData.objects.select_related(
                'route__origin', 'route__destination', 'route__airline'
            ).all()
            
            data = []
            for flight in flights:
                data.append({
                    'flight_number': flight.flight_number,
                    'origin_code': flight.route.origin.iata_code,
                    'origin_city': flight.route.origin.city,
                    'destination_code': flight.route.destination.iata_code,
                    'destination_city': flight.route.destination.city,
                    'airline': flight.route.airline.name,
                    'departure_time': flight.departure_time,
                    'arrival_time': flight.arrival_time,
                    'price': flight.price,
                    'currency': flight.currency,
                    'booking_class': flight.booking_class,
                    'availability': flight.availability,
                    'scraped_at': flight.scraped_at
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            
            return {'success': True, 'filename': filename, 'records': len(data)}
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return {'success': False, 'error': str(e)}