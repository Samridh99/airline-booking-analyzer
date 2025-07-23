import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min
from .models import FlightData, Route, MarketDemand, Insight, Airport, Airline
import logging

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("Gemini API key not configured. AI features will use mock data.")
            self.model = None
    
    def generate_insights(self):
        """Generate AI-powered insights from flight data"""
        try:
            insights = []
            
            # Get recent flight data for analysis
            recent_flights = FlightData.objects.filter(
                scraped_at__gte=timezone.now() - timedelta(days=7)
            ).select_related('route__origin', 'route__destination', 'route__airline')
            
            if not recent_flights.exists():
                logger.warning("No recent flight data available for AI analysis")
                return self.generate_mock_insights()
            
            # Price trend analysis
            price_insights = self.analyze_price_trends(recent_flights)
            insights.extend(price_insights)
            
            # Popular routes analysis
            route_insights = self.analyze_popular_routes(recent_flights)
            insights.extend(route_insights)
            
            # Seasonal patterns
            seasonal_insights = self.analyze_seasonal_patterns()
            insights.extend(seasonal_insights)
            
            # AI-generated insights using Gemini
            if self.model:
                ai_insights = self.generate_gemini_insights(recent_flights)
                insights.extend(ai_insights)
            
            # Save insights to database
            saved_insights = []
            for insight_data in insights:
                insight, created = Insight.objects.get_or_create(
                    title=insight_data['title'],
                    defaults={
                        'description': insight_data['description'],
                        'insight_type': insight_data['type'],
                        'confidence_score': insight_data.get('confidence', 0.8),
                        'generated_by': 'AI_Processor'
                    }
                )
                if created:
                    saved_insights.append(insight)
            
            return [self.serialize_insight(insight) for insight in saved_insights]
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return self.generate_mock_insights()
    
    def generate_gemini_insights(self, flights):
        """Generate insights using Gemini API"""
        insights = []
        
        try:
            if not self.model:
                return insights
            
            # Prepare data summary for AI analysis
            flight_summary = self.prepare_flight_summary(flights)
            
            prompt = f"""
            As an airline industry analyst, analyze the following flight booking data and provide actionable insights:
            
            {flight_summary}
            
            Please provide 2-3 key insights in JSON format with the following structure:
            [
                {{
                    "title": "Insight Title",
                    "description": "Detailed description of the insight",
                    "type": "demand_forecast",
                    "confidence": 0.85
                }}
            ]
            
            Focus on practical insights that would help a hostel business understand travel patterns. Make sure the JSON is valid.
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            ai_response = response.text
            try:
                # Clean the response to extract JSON
                if '```json' in ai_response:
                    ai_response = ai_response.split('```json')[1].split('```')[0]
                elif '```' in ai_response:
                    ai_response = ai_response.split('```')[1].split('```')[0]
                
                ai_insights = json.loads(ai_response.strip())
                insights.extend(ai_insights)
            except json.JSONDecodeError:
                logger.warning("Could not parse Gemini response as JSON")
        
        except Exception as e:
            logger.error(f"Error generating Gemini insights: {str(e)}")
        
        return insights
    
    # ... (rest of the methods remain the same as before)
    
    def analyze_price_trends(self, flights):
        """Analyze price trends across routes"""
        insights = []
        
        try:
            # Group flights by route and calculate price statistics
            route_prices = {}
            for flight in flights:
                route_key = f"{flight.route.origin.iata_code}-{flight.route.destination.iata_code}"
                if route_key not in route_prices:
                    route_prices[route_key] = []
                route_prices[route_key].append(float(flight.price))
            
            # Analyze each route
            for route_key, prices in route_prices.items():
                if len(prices) < 3:  # Need at least 3 data points
                    continue
                
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                price_volatility = (max_price - min_price) / avg_price
                
                # Generate insight based on price volatility
                if price_volatility > 0.5:
                    insights.append({
                        'title': f'High Price Volatility on {route_key} Route',
                        'description': f'The {route_key} route shows significant price fluctuations with prices ranging from ${min_price:.2f} to ${max_price:.2f} (average: ${avg_price:.2f}). This indicates high demand variability or limited seat availability.',
                        'type': 'price_trend',
                        'confidence': 0.85
                    })
                elif avg_price < 200:
                    insights.append({
                        'title': f'Budget-Friendly Route: {route_key}',
                        'description': f'The {route_key} route offers competitive pricing with an average of ${avg_price:.2f}. This route shows stable, affordable pricing suitable for budget-conscious travelers.',
                        'type': 'price_trend',
                        'confidence': 0.9
                    })
        
        except Exception as e:
            logger.error(f"Error in price trend analysis: {str(e)}")
        
        return insights
    
    def analyze_popular_routes(self, flights):
        """Analyze popular routes based on flight frequency"""
        insights = []
        
        try:
            # Count flights per route
            route_counts = {}
            for flight in flights:
                route_key = f"{flight.route.origin.city} to {flight.route.destination.city}"
                route_iata = f"{flight.route.origin.iata_code}-{flight.route.destination.iata_code}"
                
                if route_key not in route_counts:
                    route_counts[route_key] = {'count': 0, 'iata': route_iata}
                route_counts[route_key]['count'] += 1
            
            # Sort routes by popularity
            sorted_routes = sorted(route_counts.items(), key=lambda x: x[1]['count'], reverse=True)
            
            # Generate insights for top routes
            for i, (route_name, data) in enumerate(sorted_routes[:3]):
                insights.append({
                    'title': f'Popular Route #{i+1}: {route_name}',
                    'description': f'{route_name} ({data["iata"]}) is showing high activity with {data["count"]} flights in the analyzed period. This route demonstrates strong market demand and frequent service availability.',
                    'type': 'popular_route',
                    'confidence': 0.9
                })
        
        except Exception as e:
            logger.error(f"Error in popular routes analysis: {str(e)}")
        
        return insights
    
    def analyze_seasonal_patterns(self):
        """Analyze seasonal booking patterns"""
        insights = []
        
        try:
            # Get flight data from the last 90 days
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=10)
            
            flights = FlightData.objects.filter(
                departure_time__date__range=[start_date, end_date]
            ).select_related('route__origin', 'route__destination')
            
            if flights.exists():
                # Analyze by day of week
                weekday_counts = {}
                weekend_prices = []
                weekday_prices = []
                
                for flight in flights:
                    weekday = flight.departure_time.weekday()
                    is_weekend = weekday >= 5
                    
                    if weekday not in weekday_counts:
                        weekday_counts[weekday] = 0
                    weekday_counts[weekday] += 1
                    
                    if is_weekend:
                        weekend_prices.append(float(flight.price))
                    else:
                        weekday_prices.append(float(flight.price))
                
                # Weekend vs weekday analysis
                if weekend_prices and weekday_prices:
                    avg_weekend_price = sum(weekend_prices) / len(weekend_prices)
                    avg_weekday_price = sum(weekday_prices) / len(weekday_prices)
                    
                    if avg_weekend_price > avg_weekday_price * 1.1:
                        insights.append({
                            'title': 'Weekend Premium Pricing Pattern',
                            'description': f'Weekend flights show premium pricing with an average of ${avg_weekend_price:.2f} compared to ${avg_weekday_price:.2f} for weekday flights. This represents a {((avg_weekend_price/avg_weekday_price - 1) * 100):.1f}% weekend premium.',
                            'type': 'seasonal_pattern',
                            'confidence': 0.85
                        })
        
        except Exception as e:
            logger.error(f"Error in seasonal pattern analysis: {str(e)}")
        
        return insights
    
    def prepare_flight_summary(self, flights):
        """Prepare a summary of flight data for AI analysis"""
        try:
            route_summary = {}
            price_data = []
            
            for flight in flights:
                route_key = f"{flight.route.origin.city}-{flight.route.destination.city}"
                if route_key not in route_summary:
                    route_summary[route_key] = {'count': 0, 'total_price': 0}
                
                route_summary[route_key]['count'] += 1
                route_summary[route_key]['total_price'] += float(flight.price)
                price_data.append(float(flight.price))
            
            # Calculate averages
            for route in route_summary:
                route_summary[route]['avg_price'] = route_summary[route]['total_price'] / route_summary[route]['count']
            
            avg_price = sum(price_data) / len(price_data) if price_data else 0
            
            summary = f"""
            Flight Data Summary:
            - Total flights analyzed: {len(flights)}
            - Average price: ${avg_price:.2f}
            - Price range: ${min(price_data):.2f} - ${max(price_data):.2f}
            - Number of unique routes: {len(route_summary)}
            
            Top Routes by Frequency:
            """
            
            sorted_routes = sorted(route_summary.items(), key=lambda x: x[1]['count'], reverse=True)
            for route, data in sorted_routes[:5]:
                summary += f"- {route}: {data['count']} flights, avg ${data['avg_price']:.2f}\n"
            
            return summary
        
        except Exception as e:
            logger.error(f"Error preparing flight summary: {str(e)}")
            return "No data available for analysis"
    
    def generate_mock_insights(self):
        """Generate mock insights when real data is not available"""
        mock_insights = [
            {
                'title': 'Sydney-Melbourne Route Shows Strong Demand',
                'description': 'The Sydney to Melbourne route demonstrates consistent high booking volume with competitive pricing averaging $180-220. This route represents a key opportunity for business travelers and weekend getaways.',
                'type': 'popular_route',
                'confidence': 0.85
            },
            {
                'title': 'Weekend Premium Pricing Detected',
                'description': 'Flight prices show a 15-25% increase during weekends across major Australian routes. This premium pricing indicates higher leisure travel demand on weekends.',
                'type': 'seasonal_pattern',
                'confidence': 0.9
            },
            {
                'title': 'Brisbane-Gold Coast Corridor Opportunity',
                'description': 'The Brisbane to Gold Coast route shows growing demand with relatively stable pricing. This short-haul route could benefit from increased frequency during peak tourist seasons.',
                'type': 'demand_forecast',
                'confidence': 0.75
            }
        ]
        
        # Save mock insights to database
        saved_insights = []
        for insight_data in mock_insights:
            insight, created = Insight.objects.get_or_create(
                title=insight_data['title'],
                defaults={
                    'description': insight_data['description'],
                    'insight_type': insight_data['type'],
                    'confidence_score': insight_data['confidence'],
                    'generated_by': 'Mock_AI_Processor'
                }
            )
            if created:
                saved_insights.append(insight)
        
        return [self.serialize_insight(insight) for insight in saved_insights]
    
    def serialize_insight(self, insight):
        """Serialize insight object for API response"""
        return {
            'id': insight.id,
            'title': insight.title,
            'description': insight.description,
            'type': insight.insight_type,
            'confidence': float(insight.confidence_score),
            'generated_by': insight.generated_by,
            'created_at': insight.created_at.isoformat()
        }