# ✈️ Airline Market Analyzer

Market demand & pricing analysis for airline routes, built for hostel business intelligence in Australia.

## 📊 Features

- **Dashboard:** Key market stats, recent flights, popular routes, and insights.
- **Routes Analysis:** Filter and compare performance of routes, airlines, average prices, and flight count.
- **Pricing Trends:** Charts show price trends and route price comparisons over time.
- **Demand Analysis:** See demand levels, search volumes, average prices, and price trends for recent routes.
- **AI Insights:** One-click generation of actionable market insights with Gemini AI.
- **Scrape Data:** Automated or manual scraping of flight and market data (sample and real API integrations).
- **API Endpoints:** RESTful endpoints for flight data, routes, demand, and insights.

## 🛠 Tech Stack

- **Backend:** Django, Django REST Framework
- **Frontend:** Bootstrap, Chart.js, JavaScript, HTML
- **Database:** SQLite (default, easy to switch)
- **AI:** Google Gemini API (for insights)
- **Data Sources:** Sample Data Generator, Amadeus API (fallback), AviationStack (optional), OpenSky Network (optional)

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/airline-market-analyzer.git
cd airline-market-analyzer
```

### 2. Create a Virtual Environment & Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory with the following (fill your keys):

```
SECRET_KEY=your-django-secret-key
DEBUG=True
GEMINI_API_KEY=your_gemini_api_key
AMADEUS_API_KEY=your_amadeus_api_key
AMADEUS_API_SECRET=your_amadeus_api_secret
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
```

### 4. Database Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Run the Development Server

```bash
python manage.py runserver
```
Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## ⚡ Usage

- **Scrape Data:** Use the "Scrape Data" button to fetch sample or real data.
- **Dashboard:** View latest market statistics.
- **Routes:** Analyze route performance.
- **Pricing:** See price trends and comparisons.
- **Demand:** Analyze demand levels per route.
- **Insights:** Click "Generate AI Insights" for market trends.

## 🧑‍💻 Development

- **Static files:** Place CSS/JS in `static/css` and `static/js` folders.
- **Templates:** Edit UI in `templates/analyzer/*.html`.
- **Backend Logic:** Main logic in `analyzer/views.py`, `analyzer/scraper.py`, `analyzer/ai_processor.py`.

## 🔌 API Integrations

- **Sample Data:** Always available, for demo/testing.
- **Amadeus API:** (optional) For real market insights. [Get keys here](https://developers.amadeus.com/self-service-apis).
- **AviationStack API:** (optional) For live flight data. [Sign up here](https://aviationstack.com/).
- **OpenSky Network:** (optional) For real-time flight states. [Info here](https://opensky-network.org/).
- **Gemini API:** (optional) For AI-powered insights. [Get API key](https://aistudio.google.com/app/apikey).

## 🐞 Troubleshooting

- **Static Files Not Loading:** Ensure `STATIC_URL = '/static/'` and `STATICFILES_DIRS = [ BASE_DIR / 'static' ]` are set in `settings.py`.
- **API Errors:** Check your API keys and subscription. Free tiers may restrict endpoints.
- **Database Constraint Errors:** Make sure sample data provides all required fields.
- **No Data in Charts:** Scrape data first, or check the date range in views.
- **AI Key Errors:** Ensure your Gemini API key is valid and set in `.env`.

## 📂 Project Structure

```
airline-market-analyzer/
│
├── analyzer/                   # Django app
│   ├── migrations/
│   ├── templates/analyzer/     # HTML templates
│   ├── models.py
│   ├── views.py
│   ├── scraper.py
│   ├── ai_processor.py
│   ├── aviationstack_client.py
│   └── ...
├── airline_analyzer/           # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── static/css/             # CSS files                    # Static root directory
├── static/js/              # JavaScript files
├── manage.py
├── requirements.txt
├── .env
└── README.md
```


## 📝 License

MIT License. See [LICENSE](LICENSE).

## 👨‍💻 Author

Developed by [YOUR NAME](https://github.com/YOUR_GITHUB_USERNAME)