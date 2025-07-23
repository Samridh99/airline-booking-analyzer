import requests
import json
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import FlightData, Route, Airline, Airport, MarketDemand
import logging

logger = logging.getLogger(__name__)

class AmadeusClient:
    def __init__(self):
        self.api_key = getattr(settings, 'AMADEUS_API_KEY', None)
        self.api_secret = getattr(settings, 'AMADEUS_API_SECRET', None)
        self.base_url = "https://test.api.amadeus.com"  # Use test environment
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self):
        """Get OAuth2 access token from Amadeus"""
        try:
            if not self.api_key or not self.api_secret:
                raise Exception("Amadeus API credentials not configured")
                
            if self.access_token and self.token_expires_at > datetime.now():
                return self.access_token
            
            url = f"{self.base_url}/v1/security/oauth2/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.api_secret
            }
            
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 1799)  # Default 30 minutes
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.access_token
            
        except Exception as e:
            logger.error(f"Error getting Amadeus access token: {str(e)}")
            raise
    
    def make_api_request(self, endpoint, params=None):
        """Make authenticated request to Amadeus API"""
        try:
            token = self.get_access_token()
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error making Amadeus API request: {str(e)}")
            raise
    
    def get_most_traveled_destinations(self, origin_city_code, period=None):
        """Get most traveled destinations from origin city"""
        try:
            if not period:
                # FIXED: Use a historical period that exists in Amadeus test data
                # Amadeus test API typically has data for 2017-2019
                period = '2017-08'  # Use August 2017 as default test period
            
            endpoint = "/v1/travel/analytics/air-traffic/traveled"
            params = {
                'originCityCode': origin_city_code,
                'period': period,
                'max': 10
            }
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting most traveled destinations: {str(e)}")
            return None

    def get_most_booked_destinations(self, origin_city_code, period=None):
        """Get most booked destinations from origin city"""
        try:
            if not period:
                # FIXED: Use a historical period that exists in Amadeus test data
                period = '2017-08'  # Use August 2017 as default test period
            
            endpoint = "/v1/travel/analytics/air-traffic/booked"
            params = {
                'originCityCode': origin_city_code,
                'period': period,
                'max': 10
            }
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting most booked destinations: {str(e)}")
            return None

    def get_busiest_traveling_period(self, city_code, direction='DEPARTING'):
        """Get busiest traveling periods for a city"""
        try:
            endpoint = "/v1/travel/analytics/air-traffic/busiest-period"
            params = {
                'cityCode': city_code,
                'direction': direction,
                'period': '2017'  # FIXED: Use 2017 instead of 2024
            }
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting busiest traveling period: {str(e)}")
            return None

class FlightScraper:
    def __init__(self):
        self.amadeus_client = AmadeusClient()
        
    def scrape_amadeus_data(self):
        """Scrape real data from Amadeus APIs"""
        try:
            results = {
                'flights_added': 0,
                'routes_analyzed': 0,
                'market_data_added': 0,
                'success': True
            }
            
            # Check if Amadeus credentials are available
            if not self.amadeus_client.api_key or not self.amadeus_client.api_secret:
                logger.warning("Amadeus credentials not available, falling back to sample data")
                return self.scrape_sample_data()
            
            # Australian city codes for analysis
            australian_cities = ['SYD', 'MEL', 'BNE', 'PER']  # Reduced to avoid rate limits
            amadeus_success = False
            
            for origin_city in australian_cities:
                try:
                    # Get most traveled destinations
                    traveled_data = self.amadeus_client.get_most_traveled_destinations(origin_city)
                    if traveled_data and 'data' in traveled_data:
                        self.process_traveled_destinations(origin_city, traveled_data['data'])
                        results['routes_analyzed'] += len(traveled_data['data'])
                        amadeus_success = True
                    
                    # Get most booked destinations
                    booked_data = self.amadeus_client.get_most_booked_destinations(origin_city)
                    if booked_data and 'data' in booked_data:
                        self.process_booked_destinations(origin_city, booked_data['data'])
                        results['market_data_added'] += len(booked_data['data'])
                        amadeus_success = True
                    
                    # Small delay to respect rate limits
                    import time
                    time.sleep(1.0)  # Increased delay
                    
                except Exception as e:
                    logger.error(f"Error processing city {origin_city}: {str(e)}")
                    continue
            
            # If Amadeus API failed completely, fall back to sample data
            if not amadeus_success:
                logger.warning("Amadeus API failed completely, generating sample data instead")
                return self.scrape_sample_data()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Amadeus data scraping: {str(e)}")
            # Fall back to sample data on error
            logger.info("Falling back to sample data generation")
            return self.scrape_sample_data()
    
    def process_traveled_destinations(self, origin_city, destinations_data):
        """Process traveled destinations data"""
        try:
            for dest_data in destinations_data:
                destination_code = dest_data.get('destination')
                travelers_score = dest_data.get('analytics', {}).get('travelers', {}).get('score', 0)
                
                # Create or get airports
                origin_airport = self.get_or_create_airport(origin_city)
                dest_airport = self.get_or_create_airport(destination_code)
                
                if origin_airport and dest_airport:
                    # Create route if it doesn't exist
                    route, created = Route.objects.get_or_create(
                        origin=origin_airport,
                        destination=dest_airport,
                        airline=self.get_default_airline(),
                        defaults={'distance': random.randint(500, 4000)}
                    )
                    
                    # Create market demand record
                    MarketDemand.objects.update_or_create(
                        route=route,
                        date=timezone.now().date(),
                        defaults={
                            'search_volume': int(travelers_score * 100),  # Convert score to volume
                            'average_price': random.randint(200, 800),  # Placeholder
                            'price_trend': 'stable',
                            'demand_level': self.calculate_demand_level_from_score(travelers_score)
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error processing traveled destinations: {str(e)}")
    
    def process_booked_destinations(self, origin_city, booked_data):
        """Process booked destinations data"""
        try:
            for booking_data in booked_data:
                destination_code = booking_data.get('destination')
                travelers_score = booking_data.get('analytics', {}).get('travelers', {}).get('score', 0)
                flights_score = booking_data.get('analytics', {}).get('flights', {}).get('score', 0)
                
                # Similar processing as traveled destinations but with booking-specific logic
                origin_airport = self.get_or_create_airport(origin_city)
                dest_airport = self.get_or_create_airport(destination_code)
                
                if origin_airport and dest_airport:
                    route, created = Route.objects.get_or_create(
                        origin=origin_airport,
                        destination=dest_airport,
                        airline=self.get_default_airline(),
                        defaults={'distance': random.randint(500, 4000)}
                    )
                    
                    # Update market demand with booking data
                    MarketDemand.objects.update_or_create(
                        route=route,
                        date=timezone.now().date(),
                        defaults={
                            'search_volume': int(max(travelers_score, flights_score) * 100),
                            'average_price': random.randint(200, 800),
                            'price_trend': 'stable',
                            'demand_level': self.calculate_demand_level_from_score(max(travelers_score, flights_score))
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error processing booked destinations: {str(e)}")
    
    def process_busiest_periods(self, city_code, periods_data):
        """Process busiest traveling periods data"""
        try:
            for period_data in periods_data:
                period = period_data.get('period')
                travelers_score = period_data.get('analytics', {}).get('travelers', {}).get('score', 0)
                
                # Store seasonal pattern data
                # You can extend this to create seasonal insights
                logger.info(f"Busiest period for {city_code}: {period} with score {travelers_score}")
                
        except Exception as e:
            logger.error(f"Error processing busiest periods: {str(e)}")
    
    def get_or_create_airport(self, iata_code):
        """Get or create airport by IATA code"""
        try:
            # Map some common airport codes to names
            airport_names = {
                'SYD': {'name': 'Sydney Kingsford Smith Airport', 'city': 'Sydney', 'country': 'Australia'},
                'MEL': {'name': 'Melbourne Airport', 'city': 'Melbourne', 'country': 'Australia'},
                'BNE': {'name': 'Brisbane Airport', 'city': 'Brisbane', 'country': 'Australia'},
                'PER': {'name': 'Perth Airport', 'city': 'Perth', 'country': 'Australia'},
                'ADL': {'name': 'Adelaide Airport', 'city': 'Adelaide', 'country': 'Australia'},
                'CNS': {'name': 'Cairns Airport', 'city': 'Cairns', 'country': 'Australia'},
                'DRW': {'name': 'Darwin Airport', 'city': 'Darwin', 'country': 'Australia'},
                'OOL': {'name': 'Gold Coast Airport', 'city': 'Gold Coast', 'country': 'Australia'},
            }
            
            airport_info = airport_names.get(iata_code, {
                'name': f'{iata_code} Airport',
                'city': iata_code,
                'country': 'Unknown'
            })
            
            airport, created = Airport.objects.get_or_create(
                iata_code=iata_code,
                defaults=airport_info
            )
            return airport
        except Exception as e:
            logger.error(f"Error creating airport {iata_code}: {str(e)}")
            return None
    
    def get_default_airline(self):
        """Get or create a default airline"""
        airline, created = Airline.objects.get_or_create(
            iata_code='XX',
            defaults={
                'name': 'Multiple Airlines',
                'country': 'International'
            }
        )
        return airline
    
    def calculate_demand_level_from_score(self, score):
        """Convert Amadeus score to demand level"""
        if score >= 30:
            return 'very_high'
        elif score >= 20:
            return 'high'
        elif score >= 10:
            return 'medium'
        else:
            return 'low'
    
    def scrape_sample_data(self):
        """
        Generate sample flight data including both past and future flights
        """
        try:
            # Create sample airlines if they don't exist
            airlines_data = [
                {'name': 'Qantas Airways', 'iata_code': 'QF', 'country': 'Australia'},
                {'name': 'Virgin Australia', 'iata_code': 'VA', 'country': 'Australia'},
                {'name': 'Jetstar Airways', 'iata_code': 'JQ', 'country': 'Australia'},
                {'name': 'Singapore Airlines', 'iata_code': 'SQ', 'country': 'Singapore'},
                {'name': 'Emirates', 'iata_code': 'EK', 'country': 'UAE'},
            ]
            
            for airline_data in airlines_data:
                airline, created = Airline.objects.get_or_create(
                    iata_code=airline_data['iata_code'],
                    defaults=airline_data
                )
            
            # Create sample airports if they don't exist
            airports_data = [
                {'name': 'Sydney Kingsford Smith Airport', 'city': 'Sydney', 'country': 'Australia', 'iata_code': 'SYD'},
                {'name': 'Melbourne Airport', 'city': 'Melbourne', 'country': 'Australia', 'iata_code': 'MEL'},
                {'name': 'Brisbane Airport', 'city': 'Brisbane', 'country': 'Australia', 'iata_code': 'BNE'},
                {'name': 'Perth Airport', 'city': 'Perth', 'country': 'Australia', 'iata_code': 'PER'},
                {'name': 'Adelaide Airport', 'city': 'Adelaide', 'country': 'Australia', 'iata_code': 'ADL'},
                {'name': 'Gold Coast Airport', 'city': 'Gold Coast', 'country': 'Australia', 'iata_code': 'OOL'},
                {'name': 'Cairns Airport', 'city': 'Cairns', 'country': 'Australia', 'iata_code': 'CNS'},
                {'name': 'Darwin Airport', 'city': 'Darwin', 'country': 'Australia', 'iata_code': 'DRW'},
            ]
            
            for airport_data in airports_data:
                airport, created = Airport.objects.get_or_create(
                    iata_code=airport_data['iata_code'],
                    defaults=airport_data
                )
            
            # Create sample routes
            routes_created = 0
            flights_added = 0
            market_data_added = 0
            
            airports = Airport.objects.all()
            airlines = Airline.objects.all()
            
            # Generate routes between major Australian cities
            for origin in airports:
                for destination in airports:
                    if origin != destination:
                        for airline in airlines:
                            route, created = Route.objects.get_or_create(
                                origin=origin,
                                destination=destination,
                                airline=airline,
                                defaults={'distance': random.randint(500, 4000)}
                            )
                            if created:
                                routes_created += 1
                            
                            # Create market demand data for this route
                            market_demand, md_created = MarketDemand.objects.get_or_create(
                                route=route,
                                date=timezone.now().date(),
                                defaults={
                                    'search_volume': random.randint(10, 100),
                                    'average_price': random.randint(200, 800),
                                    'price_trend': random.choice(['increasing', 'decreasing', 'stable']),
                                    'demand_level': random.choice(['low', 'medium', 'high', 'very_high'])
                                }
                            )
                            if md_created:
                                market_data_added += 1
                            
                            # FIXED: Generate sample flight data for BOTH past and future dates
                            # Past 15 days
                            for day in range(-15, 0):
                                flight_date = timezone.now() + timedelta(days=day)
                                
                                # Generate 1-2 flights per day for past dates
                                for flight_num in range(random.randint(1, 2)):
                                    departure_time = flight_date.replace(
                                        hour=random.randint(6, 22),
                                        minute=random.choice([0, 15, 30, 45]),
                                        second=0,
                                        microsecond=0
                                    )
                                    
                                    arrival_time = departure_time + timedelta(
                                        hours=random.randint(1, 8),
                                        minutes=random.choice([0, 15, 30, 45])
                                    )
                                    
                                    # Generate realistic prices based on route distance and time
                                    base_price = route.distance * 0.15 if route.distance else 200
                                    price_variation = random.uniform(0.7, 1.5)  # ±50% variation
                                    final_price = base_price * price_variation
                                    
                                    # Weekend and peak hour pricing
                                    if departure_time.weekday() >= 5:  # Weekend
                                        final_price *= 1.2
                                    if departure_time.hour in [7, 8, 17, 18, 19]:  # Peak hours
                                        final_price *= 1.15
                                    
                                    flight_data = FlightData.objects.create(
                                        route=route,
                                        flight_number=f"{airline.iata_code}{random.randint(100, 999)}",
                                        departure_time=departure_time,
                                        arrival_time=arrival_time,
                                        price=round(final_price, 2),
                                        currency='AUD',
                                        availability=random.randint(0, 200),
                                        booking_class=random.choice(['E', 'E', 'E', 'P', 'B']),  # Mostly economy
                                        source='Sample_Data_Generator'
                                    )
                                    flights_added += 1
                            
                            # Future 30 days
                            for day in range(30):
                                flight_date = timezone.now() + timedelta(days=day)
                                
                                # Generate 1-3 flights per day for future dates
                                for flight_num in range(random.randint(1, 3)):
                                    departure_time = flight_date.replace(
                                        hour=random.randint(6, 22),
                                        minute=random.choice([0, 15, 30, 45]),
                                        second=0,
                                        microsecond=0
                                    )
                                    
                                    arrival_time = departure_time + timedelta(
                                        hours=random.randint(1, 8),
                                        minutes=random.choice([0, 15, 30, 45])
                                    )
                                    
                                    # Generate realistic prices based on route distance and time
                                    base_price = route.distance * 0.15 if route.distance else 200
                                    price_variation = random.uniform(0.7, 1.5)  # ±50% variation
                                    final_price = base_price * price_variation
                                    
                                    # Weekend and peak hour pricing
                                    if departure_time.weekday() >= 5:  # Weekend
                                        final_price *= 1.2
                                    if departure_time.hour in [7, 8, 17, 18, 19]:  # Peak hours
                                        final_price *= 1.15
                                    
                                    flight_data = FlightData.objects.create(
                                        route=route,
                                        flight_number=f"{airline.iata_code}{random.randint(100, 999)}",
                                        departure_time=departure_time,
                                        arrival_time=arrival_time,
                                        price=round(final_price, 2),
                                        currency='AUD',
                                        availability=random.randint(0, 200),
                                        booking_class=random.choice(['E', 'E', 'E', 'P', 'B']),  # Mostly economy
                                        source='Sample_Data_Generator'
                                    )
                                    flights_added += 1
            
            return {
                'success': True,
                'routes_created': routes_created,
                'flights_added': flights_added,
                'routes_analyzed': routes_created,
                'market_data_added': market_data_added,
                'message': f'Generated {flights_added} sample flights and {market_data_added} market demand records across {routes_created} new routes'
            }
            
        except Exception as e:
            logger.error(f"Error in scrape_sample_data: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'flights_added': 0,
                'routes_created': 0,
                'routes_analyzed': 0,
                'market_data_added': 0
            }
        







# import requests
# import json
# import random
# from datetime import datetime, timedelta
# from django.utils import timezone
# from django.conf import settings
# from .models import FlightData, Route, Airline, Airport, MarketDemand
# from .aviationstack_client import AviationStackClient
# import logging

# logger = logging.getLogger(__name__)

# class FlightScraper:
#     def __init__(self):
#         self.aviationstack_client = AviationStackClient()
        
#     def scrape_real_data(self):
#         """Scrape real data from AviationStack API"""
#         try:
#             results = {
#                 'flights_added': 0,
#                 'routes_analyzed': 0,
#                 'market_data_added': 0,
#                 'success': True,
#                 'api_calls_successful': 0,
#                 'api_calls_failed': 0
#             }
            

#             if not self.aviationstack_client.api_key:
#                 logger.warning("AviationStack API key not available, falling back to sample data")
#                 return self.scrape_sample_data()
            
#             try:

#                 airports_data = self.aviationstack_client.get_airports('AU', limit=50)
#                 if airports_data and 'data' in airports_data:
#                     self.process_airports_data(airports_data['data'])
#                     results['api_calls_successful'] += 1
                

#                 airlines_data = self.aviationstack_client.get_airlines('AU', limit=20)
#                 if airlines_data and 'data' in airlines_data:
#                     self.process_airlines_data(airlines_data['data'])
#                     results['api_calls_successful'] += 1
                

#                 major_airports = ['SYD', 'MEL', 'BNE', 'PER', 'ADL']
                
#                 for airport_code in major_airports:
#                     try:

#                         flights_data = self.aviationstack_client.get_flights(dep_iata=airport_code, limit=50)
#                         if flights_data and 'data' in flights_data:
#                             flights_processed = self.process_flights_data(flights_data['data'])
#                             results['flights_added'] += flights_processed
#                             results['api_calls_successful'] += 1
                        

#                         routes_data = self.aviationstack_client.get_routes(dep_iata=airport_code, limit=30)
#                         if routes_data and 'data' in routes_data:
#                             routes_processed = self.process_routes_data(routes_data['data'])
#                             results['routes_analyzed'] += routes_processed
#                             results['market_data_added'] += routes_processed
#                             results['api_calls_successful'] += 1
                        

#                         import time
#                         time.sleep(1.0)
                        
#                     except Exception as e:
#                         logger.error(f"Error processing airport {airport_code}: {str(e)}")
#                         results['api_calls_failed'] += 1
#                         continue
                

#                 if results['flights_added'] > 0 or results['routes_analyzed'] > 0:
#                     logger.info("Got real API data, supplementing with sample data")
#                     sample_result = self.scrape_sample_data()
#                     results['flights_added'] += sample_result.get('flights_added', 0)
#                     results['message'] = f"Real data: {results['api_calls_successful']} API calls successful, {results['flights_added']} total flights"
#                 else:
#                     logger.warning("No real data obtained, generating sample data")
#                     return self.scrape_sample_data()
                
#                 return results
                
#             except Exception as e:
#                 logger.error(f"AviationStack API failed: {str(e)}")
#                 return self.scrape_sample_data()
                
#         except Exception as e:
#             logger.error(f"Error in real data scraping: {str(e)}")
#             return self.scrape_sample_data()
    
#     def process_airports_data(self, airports_data):
#         """Process airport data from AviationStack"""
#         try:
#             for airport_data in airports_data:
#                 iata_code = airport_data.get('iata_code')
#                 if not iata_code:
#                     continue
                

#                 country = self.aviationstack_client.safe_get_country(airport_data)
                
#                 airport, created = Airport.objects.get_or_create(
#                     iata_code=iata_code,
#                     defaults={
#                         'name': airport_data.get('airport_name', f'{iata_code} Airport'),
#                         'city': airport_data.get('city_name', iata_code),
#                         'country': country  # This will never be None
#                     }
#                 )
                
#                 if created:
#                     logger.info(f"Created airport: {airport.name}")
                    
#         except Exception as e:
#             logger.error(f"Error processing airports data: {str(e)}")
    
#     def process_airlines_data(self, airlines_data):
#         """Process airline data from AviationStack"""
#         try:
#             for airline_data in airlines_data:
#                 iata_code = airline_data.get('iata_code')
#                 if not iata_code:
#                     continue
                

#                 country = airline_data.get('country_name') or airline_data.get('country_code') or 'Unknown'
                
#                 airline, created = Airline.objects.get_or_create(
#                     iata_code=iata_code,
#                     defaults={
#                         'name': airline_data.get('airline_name', f'{iata_code} Airlines'),
#                         'country': country
#                     }
#                 )
                
#                 if created:
#                     logger.info(f"Created airline: {airline.name}")
                    
#         except Exception as e:
#             logger.error(f"Error processing airlines data: {str(e)}")
    
#     def process_flights_data(self, flights_data):
#         """Process flight data from AviationStack"""
#         flights_processed = 0
        
#         try:
#             for flight_data in flights_data:

#                 departure = flight_data.get('departure', {})
#                 arrival = flight_data.get('arrival', {})
#                 flight_info = flight_data.get('flight', {})
                
#                 dep_iata = departure.get('iata')
#                 arr_iata = arrival.get('iata')
                
#                 if not dep_iata or not arr_iata:
#                     continue
                

#                 dep_airport = self.get_or_create_airport_by_iata(dep_iata)
#                 arr_airport = self.get_or_create_airport_by_iata(arr_iata)
                
#                 if not dep_airport or not arr_airport:
#                     continue
                

#                 airline_iata = flight_info.get('iata')
#                 airline = self.get_or_create_airline_by_iata(airline_iata)
                

#                 route, created = Route.objects.get_or_create(
#                     origin=dep_airport,
#                     destination=arr_airport,
#                     airline=airline,
#                     defaults={'distance': random.randint(500, 4000)}
#                 )
                

#                 try:
#                     dep_time_str = departure.get('scheduled')
#                     arr_time_str = arrival.get('scheduled')
                    
#                     if dep_time_str and arr_time_str:
#                         dep_time = datetime.fromisoformat(dep_time_str.replace('Z', '+00:00'))
#                         arr_time = datetime.fromisoformat(arr_time_str.replace('Z', '+00:00'))
                        

#                         base_price = route.distance * 0.12 if route.distance else 300
#                         price_variation = random.uniform(0.8, 1.4)
#                         final_price = base_price * price_variation
                        

#                         flight_number = self.aviationstack_client.safe_get_flight_number(flight_data)
                        

#                         if not flight_number:
#                             flight_number = f"{airline.iata_code}{random.randint(100, 999)}"
                        

#                         flight_record, created = FlightData.objects.get_or_create(
#                             route=route,
#                             flight_number=flight_number,  # This will never be None
#                             departure_time=dep_time,
#                             defaults={
#                                 'arrival_time': arr_time,
#                                 'price': round(final_price, 2),
#                                 'currency': 'AUD',
#                                 'availability': random.randint(0, 200),
#                                 'booking_class': 'E',
#                                 'source': 'AviationStack_API'
#                             }
#                         )
                        
#                         if created:
#                             flights_processed += 1
                            
#                 except Exception as e:
#                     logger.warning(f"Error parsing flight times: {str(e)}")
#                     continue
                    
#         except Exception as e:
#             logger.error(f"Error processing flights data: {str(e)}")
        
#         return flights_processed
    
#     def process_routes_data(self, routes_data):
#         """Process route data from AviationStack"""
#         routes_processed = 0
        
#         try:
#             for route_data in routes_data:
#                 dep_iata = route_data.get('departure_iata')
#                 arr_iata = route_data.get('arrival_iata')
#                 airline_iata = route_data.get('airline_iata')
                
#                 if not dep_iata or not arr_iata:
#                     continue
                

#                 dep_airport = self.get_or_create_airport_by_iata(dep_iata)
#                 arr_airport = self.get_or_create_airport_by_iata(arr_iata)
#                 airline = self.get_or_create_airline_by_iata(airline_iata)
                
#                 if not dep_airport or not arr_airport:
#                     continue
                

#                 route, created = Route.objects.get_or_create(
#                     origin=dep_airport,
#                     destination=arr_airport,
#                     airline=airline,
#                     defaults={'distance': random.randint(500, 4000)}
#                 )
                

#                 market_demand, md_created = MarketDemand.objects.get_or_create(
#                     route=route,
#                     date=timezone.now().date(),
#                     defaults={
#                         'search_volume': random.randint(20, 80),
#                         'average_price': random.randint(250, 750),
#                         'price_trend': random.choice(['increasing', 'decreasing', 'stable']),
#                         'demand_level': random.choice(['low', 'medium', 'high', 'very_high'])
#                     }
#                 )
                
#                 if created or md_created:
#                     routes_processed += 1
                    
#         except Exception as e:
#             logger.error(f"Error processing routes data: {str(e)}")
        
#         return routes_processed
    
#     def get_or_create_airport_by_iata(self, iata_code):
#         """Get or create airport by IATA code with safe defaults"""
#         if not iata_code:
#             return None
            
#         try:
#             airport, created = Airport.objects.get_or_create(
#                 iata_code=iata_code,
#                 defaults={
#                     'name': f'{iata_code} Airport',
#                     'city': iata_code,
#                     'country': 'Unknown'  # Ensure country is never None
#                 }
#             )
#             return airport
#         except Exception as e:
#             logger.error(f"Error creating airport {iata_code}: {str(e)}")
#             return None
    
#     def get_or_create_airline_by_iata(self, iata_code):
#         """Get or create airline by IATA code with safe defaults"""
#         if not iata_code:

#             airline, created = Airline.objects.get_or_create(
#                 iata_code='XX',
#                 defaults={
#                     'name': 'Unknown Airline',
#                     'country': 'Unknown'  # Ensure country is never None
#                 }
#             )
#             return airline
            
#         try:
#             airline, created = Airline.objects.get_or_create(
#                 iata_code=iata_code,
#                 defaults={
#                     'name': f'{iata_code} Airlines',
#                     'country': 'Unknown'  # Ensure country is never None
#                 }
#             )
#             return airline
#         except Exception as e:
#             logger.error(f"Error creating airline {iata_code}: {str(e)}")

#             airline, created = Airline.objects.get_or_create(
#                 iata_code='XX',
#                 defaults={
#                     'name': 'Unknown Airline',
#                     'country': 'Unknown'
#                 }
#             )
#             return airline
    
#     def generate_safe_flight_number(self, airline_iata=None):
#         """Generate a safe flight number"""
#         if not airline_iata:
#             airline_iata = 'XX'
#         return f"{airline_iata}{random.randint(100, 999)}"
    
#     def scrape_sample_data(self):
#         """
#         Generate sample flight data including both past and future flights
#         """
#         try:

#             airlines_data = [
#                 {'name': 'Qantas Airways', 'iata_code': 'QF', 'country': 'Australia'},
#                 {'name': 'Virgin Australia', 'iata_code': 'VA', 'country': 'Australia'},
#                 {'name': 'Jetstar Airways', 'iata_code': 'JQ', 'country': 'Australia'},
#                 {'name': 'Singapore Airlines', 'iata_code': 'SQ', 'country': 'Singapore'},
#                 {'name': 'Emirates', 'iata_code': 'EK', 'country': 'UAE'},
#             ]
            
#             for airline_data in airlines_data:
#                 airline, created = Airline.objects.get_or_create(
#                     iata_code=airline_data['iata_code'],
#                     defaults=airline_data
#                 )
            

#             airports_data = [
#                 {'name': 'Sydney Kingsford Smith Airport', 'city': 'Sydney', 'country': 'Australia', 'iata_code': 'SYD'},
#                 {'name': 'Melbourne Airport', 'city': 'Melbourne', 'country': 'Australia', 'iata_code': 'MEL'},
#                 {'name': 'Brisbane Airport', 'city': 'Brisbane', 'country': 'Australia', 'iata_code': 'BNE'},
#                 {'name': 'Perth Airport', 'city': 'Perth', 'country': 'Australia', 'iata_code': 'PER'},
#                 {'name': 'Adelaide Airport', 'city': 'Adelaide', 'country': 'Australia', 'iata_code': 'ADL'},
#                 {'name': 'Gold Coast Airport', 'city': 'Gold Coast', 'country': 'Australia', 'iata_code': 'OOL'},
#                 {'name': 'Cairns Airport', 'city': 'Cairns', 'country': 'Australia', 'iata_code': 'CNS'},
#                 {'name': 'Darwin Airport', 'city': 'Darwin', 'country': 'Australia', 'iata_code': 'DRW'},
#             ]
            
#             for airport_data in airports_data:
#                 airport, created = Airport.objects.get_or_create(
#                     iata_code=airport_data['iata_code'],
#                     defaults=airport_data
#                 )
            

#             routes_created = 0
#             flights_added = 0
#             market_data_added = 0
            
#             airports = Airport.objects.all()
#             airlines = Airline.objects.all()
            

#             for origin in airports:
#                 for destination in airports:
#                     if origin != destination:
#                         for airline in airlines:
#                             route, created = Route.objects.get_or_create(
#                                 origin=origin,
#                                 destination=destination,
#                                 airline=airline,
#                                 defaults={'distance': random.randint(500, 4000)}
#                             )
#                             if created:
#                                 routes_created += 1
                            

#                             market_demand, md_created = MarketDemand.objects.get_or_create(
#                                 route=route,
#                                 date=timezone.now().date(),
#                                 defaults={
#                                     'search_volume': random.randint(10, 100),
#                                     'average_price': random.randint(200, 800),
#                                     'price_trend': random.choice(['increasing', 'decreasing', 'stable']),
#                                     'demand_level': random.choice(['low', 'medium', 'high', 'very_high'])
#                                 }
#                             )
#                             if md_created:
#                                 market_data_added += 1
                            


#                             for day in range(-15, 0):
#                                 flight_date = timezone.now() + timedelta(days=day)
                                
#                                 # Generate 1-2 flights per day for past dates
#                                 for flight_num in range(random.randint(1, 2)):
#                                     departure_time = flight_date.replace(
#                                         hour=random.randint(6, 22),
#                                         minute=random.choice([0, 15, 30, 45]),
#                                         second=0,
#                                         microsecond=0
#                                     )
                                    
#                                     arrival_time = departure_time + timedelta(
#                                         hours=random.randint(1, 8),
#                                         minutes=random.choice([0, 15, 30, 45])
#                                     )
                                    

#                                     base_price = route.distance * 0.15 if route.distance else 200
#                                     price_variation = random.uniform(0.7, 1.5)  # ±50% variation
#                                     final_price = base_price * price_variation
                                    

#                                     if departure_time.weekday() >= 5:  # Weekend
#                                         final_price *= 1.2
#                                     if departure_time.hour in [7, 8, 17, 18, 19]:  # Peak hours
#                                         final_price *= 1.15
                                    

#                                     flight_number = self.generate_safe_flight_number(airline.iata_code)
                                    
#                                     flight_data = FlightData.objects.create(
#                                         route=route,
#                                         flight_number=flight_number,  # Always has a value
#                                         departure_time=departure_time,
#                                         arrival_time=arrival_time,
#                                         price=round(final_price, 2),
#                                         currency='AUD',
#                                         availability=random.randint(0, 200),
#                                         booking_class=random.choice(['E', 'E', 'E', 'P', 'B']),  # Mostly economy
#                                         source='Sample_Data_Generator'
#                                     )
#                                     flights_added += 1
                            

#                             for day in range(30):
#                                 flight_date = timezone.now() + timedelta(days=day)
                                

#                                 for flight_num in range(random.randint(1, 3)):
#                                     departure_time = flight_date.replace(
#                                         hour=random.randint(6, 22),
#                                         minute=random.choice([0, 15, 30, 45]),
#                                         second=0,
#                                         microsecond=0
#                                     )
                                    
#                                     arrival_time = departure_time + timedelta(
#                                         hours=random.randint(1, 8),
#                                         minutes=random.choice([0, 15, 30, 45])
#                                     )
                                    

#                                     base_price = route.distance * 0.15 if route.distance else 200
#                                     price_variation = random.uniform(0.7, 1.5)  # ±50% variation
#                                     final_price = base_price * price_variation
                                    

#                                     if departure_time.weekday() >= 5:  # Weekend
#                                         final_price *= 1.2
#                                     if departure_time.hour in [7, 8, 17, 18, 19]:  # Peak hours
#                                         final_price *= 1.15
                                    

#                                     flight_number = self.generate_safe_flight_number(airline.iata_code)
                                    
#                                     flight_data = FlightData.objects.create(
#                                         route=route,
#                                         flight_number=flight_number,  # Always has a value
#                                         departure_time=departure_time,
#                                         arrival_time=arrival_time,
#                                         price=round(final_price, 2),
#                                         currency='AUD',
#                                         availability=random.randint(0, 200),
#                                         booking_class=random.choice(['E', 'E', 'E', 'P', 'B']),  # Mostly economy
#                                         source='Sample_Data_Generator'
#                                     )
#                                     flights_added += 1
            
#             return {
#                 'success': True,
#                 'routes_created': routes_created,
#                 'flights_added': flights_added,
#                 'routes_analyzed': routes_created,
#                 'market_data_added': market_data_added,
#                 'message': f'Generated {flights_added} sample flights and {market_data_added} market demand records across {routes_created} new routes'
#             }
            
#         except Exception as e:
#             logger.error(f"Error in scrape_sample_data: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'flights_added': 0,
#                 'routes_created': 0,
#                 'routes_analyzed': 0,
#                 'market_data_added': 0
#             }
    

#     def scrape_amadeus_data(self):
#         """Main scraping method - now uses AviationStack instead of Amadeus"""
#         return self.scrape_real_data()