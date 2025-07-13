# Web Scraping Tool for Company Information Extraction

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Selenium](https://img.shields.io/badge/Selenium-4.0+-orange.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)

A powerful web scraping tool that extracts detailed company information from search queries or seed URLs, designed for lead generation and market research.

## Features Implemented

### Core Features (Minimal Requirements)
✅ **Input Handling**
- Accepts search queries (e.g., "cloud computing startups in Europe")
- Accepts seed URLs (space-separated list)
- URL validation and normalization

✅ **Basic Data Extraction (Level 1)**
- Company name detection
- Website URL extraction
- Email addresses and phone numbers
- Output formats: CSV, JSON, SQLite

✅ **Error Handling**
- Network error recovery
- Proxy rotation
- Comprehensive logging

### Enhanced Features (Optional)
🔹 **Medium Data Extraction (Level 2)**
- Social media profiles (LinkedIn, Twitter, Facebook)
- Company descriptions
- Physical addresses
- Founding year detection

🔹 **Advanced Data Extraction (Level 3)**
- Technology stack analysis (via BuiltWith API)
- Current projects detection
- Competitor mentions
- Market positioning analysis

🔹 **Dynamic Content Handling**
- Headless Chrome browser via Selenium
- Smart waiting for JavaScript rendering
- AJAX content extraction

🔹 **URL Discovery**
- Sitemap parsing
- Domain-limited crawling (configurable depth)
- Pagination handling for search results

🔹 **Configuration Options**
- Custom selectors via YAML config
- CLI arguments for all parameters
- Rate limiting controls

🔹 **Web Dashboard**
- Real-time progress monitoring
- Interactive job control
- Results visualization
- Scheduled scraping jobs

###Implemented Features

✔️ Core Features:

User authentication (JWT/OAuth)
Dashboard with [list key features, e.g., real-time data visualization, CRUD operations]
Responsive UI using Tailwind CSS
[Add any other notable features]
✔️ Data Extraction Levels Demonstrated:

Basic: [E.g., CSV/API data import, simple filtering]
Medium: [E.g., pagination, search functionality]
Advanced: [E.g., real-time updates, WebSocket integration]

## Setup Instructions

### Prerequisites
- Python 3.8+
- Chrome browser installed
- BuiltWith API key (for tech stack analysis)

### Installation
git clone https://github.com/yourusername/company-scraper.git
cd company-scraper
pip install -r requirements.txt

### Running command 
python scraper.py --web 
Access dashboard at: http://localhost:5001 
