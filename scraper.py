import os
import re
import time
import random
import argparse
import logging
from logging.handlers import RotatingFileHandler
import yaml
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin
from tldextract import extract
from flask import Flask, render_template, jsonify, request
import threading
import json
from datetime import datetime
import sys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException

# Initialize Flask app first
app = Flask(__name__, template_folder='templates')

# Configure logging after imports
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = RotatingFileHandler(
    'scraper.log', maxBytes=5*1024*1024, backupCount=3
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Global variables
current_job = None
scraping_status = {
    "status": "idle",
    "start_time": None,
    "end_time": None,
    "urls_scraped": 0,
    "total_urls": 0,
    "errors": 0
}

class CompanyScraper:
    def __init__(self, config_path='config.yaml'):
        self.load_config(config_path)
        self.driver = self.init_webdriver()
        self.data = []
        self.visited_urls = set()
        self.errors = 0
        self.start_time = datetime.now()
        self.cli_selectors = {}
        
    def load_config(self, path):
        try:
            with open(path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.builtwith_api = self.config.get('builtwith_api', '')
            self.user_agents = self.config.get('user_agents', [])
            self.selectors = self.config.get('selectors', {})
            self.proxies = self.config.get('proxies', [])
            self.rate_limit = self.config.get('rate_limit', 3)
            self.min_delay = self.config.get('min_delay', 2)
            self.max_delay = self.config.get('max_delay', 5)
            self.test_config = self.config.get('tests', {})
            logging.info("Configuration loaded successfully")
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            raise
        
    def init_webdriver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        if self.user_agents:
            ua = random.choice(self.user_agents)
            options.add_argument(f"user-agent={ua}")
            logging.info(f"Using user agent: {ua[:50]}...")
            
        if self.proxies:
            proxy = random.choice(self.proxies)
            options.add_argument(f'--proxy-server={proxy}')
            logging.info(f"Using proxy: {proxy}")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Add human-like behavior
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logging.info("WebDriver initialized successfully")
            return driver
        except Exception as e:
            logging.error(f"WebDriver initialization failed: {str(e)}")
            raise
    
    def rotate_proxy(self):
        if not self.proxies:
            return
            
        try:
            self.driver.quit()
            proxy = random.choice(self.proxies)
            options = Options()
            options.add_argument("--headless")
            options.add_argument(f'--proxy-server={proxy}')
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            
            if self.user_agents:
                options.add_argument(f"user-agent={random.choice(self.user_agents)}")
                
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logging.info(f"Rotated to proxy: {proxy}")
        except Exception as e:
            logging.error(f"Proxy rotation failed: {str(e)}")
        
    def rotate_user_agent(self):
        if not self.user_agents:
            return
            
        try:
            new_agent = random.choice(self.user_agents)
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": new_agent}
            )
            logging.info(f"Rotated user agent to: {new_agent[:50]}...")
        except Exception as e:
            logging.error(f"User agent rotation failed: {str(e)}")
        
    def validate_url(self, url):
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
                
            headers = {'User-Agent': random.choice(self.user_agents)} if self.user_agents else {}
            proxies = {'https': random.choice(self.proxies)} if self.proxies else None
            
            response = requests.head(
                url, 
                headers=headers, 
                proxies=proxies,
                timeout=5, 
                allow_redirects=True
            )
            return response.status_code == 200, url
        except Exception as e:
            logging.error(f"URL validation error: {str(e)}")
            return False, url
            
    def get_search_results(self, query, pages=3, max_retries=3):
        urls = []
        for page in range(pages):
            for attempt in range(max_retries):
                try:
                    start = page * 10
                    search_url = f"https://www.bing.com/search?q={query}&first={start}"
                    logging.info(f"Searching: {query} (page {page+1}, attempt {attempt+1})")
                    
                    # Add human-like delay
                    time.sleep(random.uniform(1.5, 3.5))
                    
                    self.driver.get(search_url)
                    
                    # Human-like interactions
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(random.randint(10, 100), random.randint(10, 100)).perform()
                    
                    # Wait for results to load
                    try:
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "ol#b_results"))
                        )
                    except TimeoutException:
                        logging.warning("Timed out waiting for search results")
                        raise
                    
                    # Check for CAPTCHA
                    page_text = self.driver.page_source.lower()
                    if "captcha" in page_text or "sorry" in page_text or "security check" in page_text:
                        logging.warning("Search engine detection triggered")
                        raise Exception("Search engine anti-bot detection triggered")
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    new_urls = []
                    
                    # Bing search result extraction
                    for result in soup.select("ol#b_results li.b_algo h2 a"):
                        try:
                            href = result.get('href')
                            if href and urlparse(href).netloc:
                                valid, clean_url = self.validate_url(href)
                                if valid and clean_url not in urls:
                                    new_urls.append(clean_url)
                        except Exception as e:
                            logging.warning(f"URL extraction error: {str(e)}")
                    
                    if not new_urls:
                        if attempt < max_retries - 1:
                            raise Exception("No valid URLs extracted")
                        else:
                            logging.warning(f"No URLs found on page {page+1}")
                    
                    urls.extend(new_urls)
                    logging.info(f"Found {len(new_urls)} URLs on page {page+1}")
                    
                    # Scroll and random mouse movement
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50)).perform()
                    time.sleep(random.uniform(0.8, 2.0))
                    break
                except Exception as e:
                    self.errors += 1
                    logging.warning(f"Attempt {attempt+1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        logging.info("Retrying...")
                        self.rotate_user_agent()
                        self.rotate_proxy()
                        time.sleep(5 * (attempt + 1))
                    else:
                        logging.error(f"Failed page {page+1} after {max_retries} attempts")
        
        return [url for url in urls if self.validate_url(url)[0]]
        
    def extract_tech_stack(self, domain):
        if not self.builtwith_api:
            return ""
            
        try:
            url = f"https://api.builtwith.com/v19/api.json?KEY={self.builtwith_api}&LOOKUP={domain}"
            headers = {'User-Agent': random.choice(self.user_agents)} if self.user_agents else {}
            proxies = {'https': random.choice(self.proxies)} if self.proxies else None
            
            response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            if response.status_code == 200:
                data = response.json()
                tech = []
                for result in data.get('Results', []):
                    for path in result.get('Result', {}).get('Paths', []):
                        for tech_group in path.get('Technologies', []):
                            tech.append(tech_group.get('Name', ''))
                return ", ".join(filter(None, tech))
            else:
                logging.warning(f"BuiltWith API returned status {response.status_code}")
        except Exception as e:
            logging.error(f"BuiltWith API error: {str(e)}")
        return ""
        
    def extract_emails(self, text):
        if not text:
            return ""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return ", ".join(sorted(set(emails))) if emails else ""
        
    def extract_phones(self, text):
        phone_pattern = r'(\+\d{1,2}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b'
        phones = re.findall(phone_pattern, text)
        cleaned_phones = ["".join(filter(None, phone)).strip() for phone in phones]
        return ", ".join(set(cleaned_phones)) if cleaned_phones else ""
        
    def extract_using_selectors(self, soup, selector_type):
        results = []
        selectors = self.selectors.get(selector_type, [])
        if self.cli_selectors and selector_type in self.cli_selectors:
            selectors = self.cli_selectors[selector_type]
            
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    elements = self.driver.find_elements(By.XPATH, selector.split('@')[0])
                    for element in elements:
                        if '@content' in selector:
                            results.append(element.get_attribute('content').strip())
                        elif '@href' in selector:
                            results.append(element.get_attribute('href').strip())
                        else:
                            results.append(element.text.strip())
                elif selector.startswith('regex:'):
                    pattern = selector.split('regex:', 1)[1].strip()
                    matches = re.findall(pattern, str(soup))
                    results.extend(matches)
                else:
                    elements = soup.select(selector)
                    for element in elements:
                        if 'meta' in selector:
                            results.append(element.get('content', '').strip())
                        elif element.text.strip():
                            results.append(element.text.strip())
            except Exception as e:
                logging.warning(f"Selector error ({selector}): {str(e)}")
                
        return ", ".join(filter(None, set(results)))
        
    def scrape_page(self, url, level='basic'):
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        
        logging.info(f"Scraping: {url}")
        company_data = {
            'url': url,
            'name': '',
            'website': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'twitter': '',
            'facebook': '',
            'description': '',
            'address': '',
            'tech_stack': '',
            'scrape_time': datetime.now().isoformat(),
            'status': 'success'
        }
        
        try:
            # Add random delay before request
            time.sleep(random.uniform(self.min_delay, self.max_delay))
            
            self.driver.get(url)
            
            # Human-like interactions
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(10, 50), random.randint(10, 50)).perform()
            
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            except TimeoutException:
                logging.warning(f"Timed out loading page: {url}")
                raise
            
            domain = extract(url).registered_domain
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            company_data['name'] = self.extract_using_selectors(soup, 'company_name') or domain
            company_data['website'] = domain
            company_data['email'] = self.extract_emails(page_text)
            company_data['phone'] = self.extract_phones(page_text)
            
            if level in ('medium', 'advanced'):
                company_data['description'] = self.extract_using_selectors(soup, 'description')
                company_data['address'] = self.extract_using_selectors(soup, 'address')
                
                social_links = self.extract_using_selectors(soup, 'social').split(", ")
                for link in social_links:
                    if 'linkedin.com' in link: company_data['linkedin'] = link
                    if 'twitter.com' in link: company_data['twitter'] = link
                    if 'facebook.com' in link: company_data['facebook'] = link
            
            if level == 'advanced':
                company_data['tech_stack'] = self.extract_tech_stack(domain)
            
            self.data.append(company_data)
            logging.info(f"Extracted data from {url}")
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            company_data['status'] = f"error: {str(e)}"
            self.data.append(company_data)
            self.errors += 1
            self.rotate_proxy()
        
        # Add random delay after request
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        
    def discover_urls(self, seed_url, depth=1):
        if depth <= 0:
            return
            
        try:
            self.driver.get(seed_url)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    full_url = urljoin(seed_url, href)
                    if extract(full_url).registered_domain == extract(seed_url).registered_domain:
                        if full_url not in self.visited_urls:
                            self.scrape_page(full_url)
                            self.discover_urls(full_url, depth-1)
        except Exception as e:
            logging.error(f"URL discovery error: {str(e)}")
            self.errors += 1
            
    def export_data(self, format='csv', filename='output'):
        if not self.data:
            logging.warning("No data to export")
            return
            
        df = pd.DataFrame(self.data)
        
        if format == 'csv':
            output_path = f"{filename}.csv"
            df.to_csv(output_path, index=False)
        elif format == 'json':
            output_path = f"{filename}.json"
            df.to_json(output_path, orient='records')
        elif format == 'sqlite':
            import sqlite3
            output_path = f"{filename}.db"
            conn = sqlite3.connect(output_path)
            df.to_sql('companies', conn, if_exists='replace', index=False)
            conn.close()
        else:
            logging.error("Unsupported export format")
            return
            
        logging.info(f"Exported data to {output_path}")
        return output_path
        
    def close(self):
        try:
            self.driver.quit()
            logging.info("WebDriver closed successfully")
        except Exception as e:
            logging.error(f"Error closing WebDriver: {str(e)}")
        
    def run_tests(self):
        results = {
            'email_extraction': False,
            'url_validation': False,
            'selector_extraction': False
        }
        
        try:
            test_text = "Contact: sales@example.com, support@test.org, bad-email@, valid@test.co.uk"
            emails = self.extract_emails(test_text)
            expected = ["sales@example.com", "support@test.org", "valid@test.co.uk"]
            actual = [e.strip() for e in emails.split(",")] if emails else []
            results['email_extraction'] = sorted(actual) == sorted(expected)
            
            test_url = "https://google.com"
            valid, clean_url = self.validate_url(test_url)
            results['url_validation'] = valid
            
            self.driver.get("https://example.com")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            title = self.extract_using_selectors(soup, 'company_name')
            results['selector_extraction'] = "Example Domain" in title
            
            logging.info("Tests completed successfully")
            return results
        except Exception as e:
            logging.error(f"Tests failed: {str(e)}")
            return results

def run_scraping_job(args):
    global current_job, scraping_status
    scraper = None  
    try:
        scraping_status = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "urls_scraped": 0,
            "total_urls": 0,
            "errors": 0,
            "message": "Starting job"
        }
        
        scraper = CompanyScraper()
        
        if args.selectors:
            try:
                scraper.cli_selectors = json.loads(args.selectors)
            except json.JSONDecodeError:
                logging.error("Invalid selector JSON format")
        
        if args.query:
            search_urls = scraper.get_search_results(args.query, args.pages)
            if not search_urls:
                raise Exception("No search results found")
                
            scraping_status['total_urls'] = len(search_urls)
            
            for i, url in enumerate(search_urls):
                scraper.scrape_page(url, args.level)
                scraping_status['urls_scraped'] = i + 1
                scraping_status['errors'] = scraper.errors
                
        elif args.urls:
            urls = args.urls.split()
            scraping_status['total_urls'] = len(urls)
            
            for i, url in enumerate(urls):
                valid, clean_url = scraper.validate_url(url)
                if valid:
                    scraper.scrape_page(clean_url, args.level)
                    if args.depth > 0:
                        scraper.discover_urls(clean_url, args.depth)
                else:
                    logging.error(f"Invalid URL: {url}")
                scraping_status['urls_scraped'] = i + 1
                scraping_status['errors'] = scraper.errors
        else:
            raise Exception("No input provided")
            
        output_path = scraper.export_data(args.format, args.output)
        scraping_status['status'] = "completed"
        scraping_status['end_time'] = datetime.now().isoformat()
        scraping_status['message'] = f"Scraped {len(scraper.data)} companies"
        scraping_status['output_path'] = output_path
        
    except Exception as e:  
        logging.error(f"Job failed: {str(e)}")
        scraping_status['status'] = "failed"
        scraping_status['message'] = str(e)
    finally:
        if scraper:  
            scraper.close()
        current_job = None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/status')
def status():
    return jsonify(scraping_status)

@app.route('/results')
def results():
    output_file = scraping_status.get('output_path', 'output.json')
    if os.path.exists(output_file) and output_file.endswith('.json'):
        try:
            with open(output_file) as f:
                data = json.load(f)
                return jsonify(data[:10])
        except:
            pass
    return jsonify([])

@app.route('/start', methods=['POST'])
def start_job():
    global current_job
    if current_job and current_job.is_alive():
        return jsonify({"status": "error", "message": "Job already running"})
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request"})
    
    args = argparse.Namespace(
        query=data.get('query', ''),
        level=data.get('level', 'basic'),
        pages=int(data.get('pages', 3)),
        format='json',
        output='output',
        depth=0,
        selectors=None,
        urls=None
    )
    
    current_job = threading.Thread(target=run_scraping_job, args=(args,))
    current_job.daemon = True
    current_job.start()
    
    return jsonify({"status": "success", "message": "Job started"})

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python_version": sys.version,
            "platform": sys.platform
        }
    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Company Information Scraper',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    input_group = parser.add_argument_group('Input Options')
    output_group = parser.add_argument_group('Output Options')
    web_group = parser.add_argument_group('Web Dashboard Options')
    advanced_group = parser.add_argument_group('Advanced Options')

    input_group.add_argument('--query', type=str, help='Search query for company information')
    input_group.add_argument('--urls', type=str, help='Seed URLs (space separated) for direct scraping')
    output_group.add_argument('--output', type=str, default='output', 
                            help='Base output filename (without extension)')
    output_group.add_argument('--format', choices=['csv', 'json', 'sqlite'], 
                            default='csv', help='Output file format')
    advanced_group.add_argument('--level', choices=['basic', 'medium', 'advanced'], 
                              default='basic', help='Data extraction depth level')
    advanced_group.add_argument('--pages', type=int, default=3, 
                              help='Number of search result pages to scrape')
    advanced_group.add_argument('--depth', type=int, default=0, 
                              help='URL discovery depth (0 for no discovery)')
    advanced_group.add_argument('--selectors', type=str, 
                              help='JSON string of custom CSS selectors')
    web_group.add_argument('--web', action='store_true', 
                         help='Start web dashboard')
    web_group.add_argument('--port', type=int, default=5001, 
                         help='Port for web dashboard')
    web_group.add_argument('--host', type=str, default='0.0.0.0',
                         help='Host to bind to')
    parser.add_argument('--test', action='store_true', 
                      help='Run test suite only')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                      help='Increase verbosity level')
    
    args = parser.parse_args()
    
    if args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose >= 2:
        logger.setLevel(logging.DEBUG)
    
    if args.web:
        @app.route('/run', methods=['GET', 'POST'])
        def run_scraper():
            if request.method == 'POST':
                try:
                    run_scraping_job(args)
                    return jsonify({"status": "success"})
                except Exception as e:
                    return jsonify({"status": "error", "message": str(e)}), 500
            return jsonify({"status": "error", "message": "Use POST method"})
        
        try:
            logging.info(f"Starting web dashboard on port {args.port}")
            app.run(host=args.host, port=args.port, debug=False)
        except OSError as e:
            if "Address already in use" in str(e):
                logging.error(f"Port {args.port} is busy. Try a different port with --port")
            else:
                logging.error(f"Failed to start server: {str(e)}")
    else:
        if args.test:
            logging.info("Running test suite")
            scraper = CompanyScraper()
            try:
                results = scraper.run_tests()
                logging.info(f"Test results: {results}")
                exit(0 if all(results.values()) else 1)
            except Exception as e:
                logging.error(f"Test failed: {str(e)}")
                exit(1)
            finally:
                scraper.close()
        else:
            try:
                logging.info("Starting scraping job")
                run_scraping_job(args)
                logging.info("Job completed successfully")
            except Exception as e:
                logging.error(f"Scraping failed: {str(e)}")
                exit(1)