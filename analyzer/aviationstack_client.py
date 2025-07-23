import requests
import json
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import FlightData, Route, Airline, Airport, MarketDemand
import logging


logger = logging.getLogger(__name__)


class AviationStackClient:
    def __init__(self):
        self.api_key = getattr(settings, 'AVIATIONSTACK_API_KEY', None)
        self.base_url = "http://api.aviationstack.com/v1"
    
    def make_api_request(self, endpoint, params=None):
        """Make request to AviationStack API"""
        try:
            if not self.api_key:
                raise Exception("AviationStack API key not configured")
            
            if params is None:
                params = {}
            
            params['access_key'] = self.api_key
            
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Successfully made AviationStack API request to {endpoint}")
            return response.json()
            
        except Exception as e:
            logger.error(f"Error making AviationStack API request to {endpoint}: {str(e)}")
            raise
    
    def get_flights(self, dep_iata=None, arr_iata=None, limit=50):
        """Get live flight data - FREE TIER ENDPOINT"""
        try:
            endpoint = "/flights"
            params = {
                'limit': limit
            }
            
            if dep_iata:
                params['dep_iata'] = dep_iata
            if arr_iata:
                params['arr_iata'] = arr_iata
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting flights: {str(e)}")
            return None
    
    def get_airports(self, country_code='AU', limit=50):
        """Get airport information - FREE TIER ENDPOINT"""
        try:
            endpoint = "/airports"
            params = {
                'country_code': country_code,
                'limit': limit
            }
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting airports: {str(e)}")
            return None
    
    def get_airlines(self, country_code='AU', limit=50):
        """Get airline information - FREE TIER ENDPOINT"""
        try:
            endpoint = "/airlines"
            params = {
                'country_code': country_code,
                'limit': limit
            }
            
            return self.make_api_request(endpoint, params)
            
        except Exception as e:
            logger.error(f"Error getting airlines: {str(e)}")
            return None
    
    def get_routes(self, dep_iata=None, arr_iata=None, limit=50):
        """Get route information - constructs routes from flight data"""
        try:
        
            flights_data = self.get_flights(dep_iata=dep_iata, arr_iata=arr_iata, limit=limit)
            
            if not flights_data or 'data' not in flights_data:
                return None
            

            routes = []
            seen_routes = set()
            
            for flight in flights_data['data']:
                if not flight or 'departure' not in flight or 'arrival' not in flight:
                    continue
                    
                departure = flight.get('departure', {})
                arrival = flight.get('arrival', {})
                
                dep_iata_code = departure.get('iata')
                arr_iata_code = arrival.get('iata')
                
                if dep_iata_code and arr_iata_code:
                    route_key = f"{dep_iata_code}-{arr_iata_code}"
                    
                    if route_key not in seen_routes:
                        seen_routes.add(route_key)
                        routes.append({
                            'departure_iata': dep_iata_code,
                            'arrival_iata': arr_iata_code,
                            'departure_airport': departure.get('airport', 'Unknown'),
                            'arrival_airport': arrival.get('airport', 'Unknown'),
                            'airline': flight.get('airline', {}).get('name', 'Unknown')
                        })
            
            return {'data': routes}
            
        except Exception as e:
            logger.error(f"Error getting routes: {str(e)}")
            return None
    
    def safe_get_flight_number(self, flight_data):
        """Safely extract flight number from flight data"""
        try:
            if not flight_data:
                return None
                

            flight_info = flight_data.get('flight', {})
            

            flight_number = (
                flight_info.get('number') or
                flight_info.get('iata') or
                flight_info.get('icao') or
                f"{flight_info.get('airline', {}).get('iata', 'XX')}{flight_info.get('number', '000')}"
            )
            
            return flight_number if flight_number else None
            
        except Exception as e:
            logger.error(f"Error extracting flight number: {str(e)}")
            return None
    
    def safe_get_country(self, airport_data):
        """Safely extract country from airport data"""
        try:
            if not airport_data:
                return 'Unknown'
                

            country = (
                airport_data.get('country_name') or
                airport_data.get('country_code') or
                airport_data.get('country_iso2') or
                'Unknown'
            )
            
            return country
            
        except Exception as e:
            logger.error(f"Error extracting country: {str(e)}")
            return 'Unknown'