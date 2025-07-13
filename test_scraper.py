import unittest
from scraper import CompanyScraper

class TestScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = CompanyScraper()
        
    def test_email_extraction(self):
        text = "Contact us at info@company.com or sales@company.com"
        emails = self.scraper.extract_emails(text)
        self.assertIn("info@company.com", emails)
        self.assertIn("sales@company.com", emails)
        
    def test_phone_extraction(self):
        text = "Call us at 123-456-7890 or (555) 123-4567"
        phones = self.scraper.extract_phones(text)
        self.assertIn("123-456-7890", phones)
        self.assertIn("(555) 123-4567", phones)
        
    def test_url_validation(self):
        valid, url = self.scraper.validate_url("https://google.com")
        self.assertTrue(valid)
        
        valid, url = self.scraper.validate_url("invalid-url")
        self.assertFalse(valid)
        
    def tearDown(self):
        self.scraper.close()

if __name__ == '__main__':
    unittest.main()