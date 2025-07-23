from django.db import models
from django.utils import timezone

class Airline(models.Model):
    name = models.CharField(max_length=100)
    iata_code = models.CharField(max_length=3, unique=True)
    icao_code = models.CharField(max_length=4, blank=True)
    country = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.iata_code})"

class Airport(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    iata_code = models.CharField(max_length=3, unique=True)
    icao_code = models.CharField(max_length=4, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.iata_code})"

class Route(models.Model):
    origin = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='origin_routes')
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='destination_routes')
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE)
    distance = models.IntegerField(null=True, blank=True)  # Distance in kilometers
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['origin', 'destination', 'airline']

    def __str__(self):
        return f"{self.origin.iata_code} → {self.destination.iata_code} ({self.airline.iata_code})"

class FlightData(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    flight_number = models.CharField(max_length=10)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='AUD')
    availability = models.IntegerField(default=0)
    booking_class = models.CharField(max_length=1, choices=[
        ('E', 'Economy'),
        ('P', 'Premium Economy'),
        ('B', 'Business'),
        ('F', 'First Class')
    ], default='E')
    scraped_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100)  # Source of data (API, website, etc.)

    def __str__(self):
        return f"{self.route} - {self.flight_number} - ${self.price}"

class MarketDemand(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    date = models.DateField()
    search_volume = models.IntegerField(default=0)
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_trend = models.CharField(max_length=20, choices=[
        ('increasing', 'Increasing'),
        ('decreasing', 'Decreasing'),
        ('stable', 'Stable')
    ])
    demand_level = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('very_high', 'Very High')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['route', 'date']

    def __str__(self):
        return f"{self.route} - {self.date} - {self.demand_level}"

class Insight(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    insight_type = models.CharField(max_length=50, choices=[
        ('price_trend', 'Price Trend'),
        ('popular_route', 'Popular Route'),
        ('seasonal_pattern', 'Seasonal Pattern'),
        ('demand_forecast', 'Demand Forecast')
    ])
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 to 1.00
    generated_by = models.CharField(max_length=100, default='AI_Analysis')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title