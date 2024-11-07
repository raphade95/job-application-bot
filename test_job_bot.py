import unittest
from unittest.mock import Mock, patch, MagicMock
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from main import JobApplicationBot
import os
import shutil
import time

class TestJobApplicationBot(unittest.TestCase):
    def setUp(self):
        # Create test directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Create a test config file
        self.test_config = 'test_config.ini'
        with open(self.test_config, 'w') as f:
            f.write('''
[LinkedIn]
login_url = https://www.linkedin.com/login
email = test@example.com
password = testpass

[Skills]
required = python,selenium
preferred = javascript,docker
min_preferred = 1

[SearchCriteria]
keywords = Software Engineer
location = Remote

[BrowserOptions]
headless = true
            ''')
    
    def tearDown(self):
        # Clean up test files and directories
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
        if os.path.exists('logs'):
            shutil.rmtree('logs')
        if os.path.exists('data'):
            shutil.rmtree('data')

    # Your existing test methods remain here...
    @patch('selenium.webdriver.Chrome')
    def test_wait_for_element(self, mock_chrome):
        """Test wait_for_element with simplified mocking approach"""
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Create a simple mock element
        mock_element = MagicMock()
        
        # Set up WebDriverWait mock to return our mock element
        def mock_until(condition):
            return mock_element
            
        bot.wait = MagicMock()
        bot.wait.until = mock_until
        
        # Mock check_for_captcha to avoid interference
        bot.check_for_captcha = Mock(return_value=(False, ""))
        
        # Test successful wait
        result = bot.wait_for_element(By.ID, "test-id")
        self.assertIsNotNone(result)
        
        # Test timeout scenario
        def mock_until_timeout(condition):
            raise TimeoutException()
            
        bot.wait.until = mock_until_timeout
        result = bot.wait_for_element(By.ID, "nonexistent-id")
        self.assertIsNone(result)

    @patch('selenium.webdriver.Chrome')
    def test_check_for_captcha(self, mock_chrome):
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Mock the driver's find_elements method for no CAPTCHA
        def find_elements_mock(by, value):
            if any(indicator in value.lower() for indicator in ['captcha', 'security']):
                return []
            return []
        bot.driver.find_elements = Mock(side_effect=find_elements_mock)
        
        # Test no CAPTCHA
        result, captcha_type = bot.check_for_captcha()
        self.assertFalse(result)
        self.assertEqual(captcha_type, "")
        
        # Test with CAPTCHA present
        bot.driver.find_elements = Mock(return_value=[MagicMock()])
        result, captcha_type = bot.check_for_captcha()
        self.assertTrue(result)
        self.assertIn(captcha_type, ['reCAPTCHA', 'hCaptcha', 'Generic'])

    # ... other existing test methods ...

    # New LinkedIn test methods
    @patch('selenium.webdriver.Chrome')
    def test_login_to_linkedin_success(self, mock_chrome):
        """Test successful LinkedIn login scenario"""
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Create mock elements
        mock_elements = {
            'username': MagicMock(),
            'password': MagicMock(),
            'submit': MagicMock(),
            'nav': MagicMock()
        }
        
        # Configure wait_for_element to return appropriate mocks
        def mock_wait_for_element(by, value, clickable=False):
            if 'username' in str(value):
                return mock_elements['username']
            elif 'password' in str(value):
                return mock_elements['password']
            elif 'submit' in str(value):
                return mock_elements['submit']
            elif 'nav' in str(value):
                return mock_elements['nav']
            return None
            
        bot.wait_for_element = Mock(side_effect=mock_wait_for_element)
        
        # Execute login
        result = bot.login_to_linkedin()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify element interactions
        mock_elements['username'].send_keys.assert_called_once_with('test@example.com')
        mock_elements['password'].send_keys.assert_called_once_with('testpass')
        mock_elements['submit'].click.assert_called_once()

    @patch('selenium.webdriver.Chrome')
    def test_login_to_linkedin_failure(self, mock_chrome):
        """Test LinkedIn login failure scenarios"""
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Test username field not found
        bot.wait_for_element = Mock(return_value=None)
        result = bot.login_to_linkedin()
        self.assertFalse(result)
        
        # Test password field not found
        def mock_wait_for_element(by, value, clickable=False):
            if 'username' in str(value):
                return MagicMock()
            return None
        bot.wait_for_element = Mock(side_effect=mock_wait_for_element)
        result = bot.login_to_linkedin()
        self.assertFalse(result)

    @patch('selenium.webdriver.Chrome')
    def test_search_linkedin_jobs_success(self, mock_chrome):
        """Test successful LinkedIn job search"""
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Create mock elements
        mock_search_box = MagicMock()
        mock_location_box = MagicMock()
        mock_results = MagicMock()
        
        # Configure wait_for_element
        def mock_wait_for_element(by, value, clickable=False):
            if 'search' in str(value).lower():
                return mock_search_box
            elif 'city' in str(value).lower():
                return mock_location_box
            elif 'results' in str(value).lower():
                return mock_results
            return None
            
        bot.wait_for_element = Mock(side_effect=mock_wait_for_element)
        
        # Execute search
        result = bot.search_linkedin_jobs("Python Developer", "San Francisco")
        
        # Verify success
        self.assertTrue(result)
        
        # Verify element interactions
        mock_search_box.clear.assert_called_once()
        mock_search_box.send_keys.assert_any_call("Python Developer")
        mock_location_box.clear.assert_called_once()
        mock_location_box.send_keys.assert_called_with("San Francisco")

    @patch('selenium.webdriver.Chrome')
    def test_search_linkedin_jobs_with_filters(self, mock_chrome):
        """Test LinkedIn job search with filters"""
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Create mock elements
        mock_elements = {
            'search_box': MagicMock(),
            'location_box': MagicMock(),
            'filter_button': MagicMock(),
            'filter_option': MagicMock(),
            'apply_button': MagicMock(),
            'results': MagicMock()
        }
        
        # Configure wait_for_element
        def mock_wait_for_element(by, value, clickable=False):
            if 'search' in str(value).lower():
                return mock_elements['search_box']
            elif 'city' in str(value).lower():
                return mock_elements['location_box']
            elif 'filters' in str(value).lower():
                return mock_elements['filter_button']
            elif 'entry level' in str(value).lower():
                return mock_elements['filter_option']
            elif 'apply' in str(value).lower():
                return mock_elements['apply_button']
            elif 'results' in str(value).lower():
                return mock_elements['results']
            return None
            
        bot.wait_for_element = Mock(side_effect=mock_wait_for_element)
        
        # Execute search with filters
        filters = {
            "experience_level": "Entry level",
            "job_type": "Full-time"
        }
        result = bot.search_linkedin_jobs("Python Developer", "San Francisco", filters)
        
        # Verify success
        self.assertTrue(result)
        
        # Verify filter interactions
        mock_elements['filter_button'].click.assert_called()
        mock_elements['filter_option'].click.assert_called()
        mock_elements['apply_button'].click.assert_called()

if __name__ == '__main__':
    unittest.main()