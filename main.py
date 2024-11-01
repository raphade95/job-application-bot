# main.py
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import configparser
import os
import json
from typing import Optional, Dict, List

class JobApplicationBot:
    def __init__(self, config_path: str = 'config.ini'):
        """Initialize the job application bot with enhanced logging and configuration."""
        self._setup_logging()
        self.config = self._load_config(config_path)
        self.applications_submitted = 0
        self.jobs_processed = 0
        self.search_results = []
        self._setup_webdriver()
        
    def _setup_logging(self) -> None:
        """Set up enhanced logging with both file and console output."""
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(
            log_dir, 
            f'job_applications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load and validate configuration from INI file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        config = configparser.ConfigParser()
        config.read(config_path)
        
        required_sections = ['LinkedIn', 'Skills', 'SearchCriteria']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
                
        return config
    
    def _setup_webdriver(self) -> None:
        """Initialize Chrome WebDriver with enhanced options."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-notifications')
            
            if 'BrowserOptions' in self.config:
                for option in self.config['BrowserOptions']:
                    options.add_argument(option)
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def login_to_portal(self, portal: str) -> bool:
        """Login to job portal with enhanced error handling and verification."""
        try:
            self.driver.get(self.config[portal]['login_url'])
            
            # Wait for and enter credentials
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.clear()
            email_field.send_keys(self.config[portal]['email'])
            
            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_field.clear()
            password_field.send_keys(self.config[portal]['password'])
            
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "login-submit"))
            )
            login_button.click()
            
            # Verify successful login
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "profile-rail-card"))
            )
            
            self.logger.info(f"Successfully logged into {portal}")
            return True
            
        except TimeoutException:
            self.logger.error(f"Timeout while logging into {portal} - element not found")
            return False
        except Exception as e:
            self.logger.error(f"Failed to login to {portal}: {str(e)}")
            return False

    def search_jobs(self, keywords: str, location: Optional[str] = None) -> bool:
        """Search for jobs based on keywords and location."""
        try:
            # Wait for search box and enter keywords
            search_box = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-box__text-input"))
            )
            search_box.clear()
            search_box.send_keys(keywords)
            
            if location:
                location_field = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-box__location-input"))
                )
                location_field.clear()
                location_field.send_keys(location)
            
            # Submit search
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-results"))
            )
            
            self.logger.info(f"Performed job search for '{keywords}' in {location if location else 'any location'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to perform job search: {str(e)}")
            return False

    def filter_job_posting(self, job_description: str) -> bool:
        """Filter job posting based on required and preferred skills."""
        try:
            required_skills = set(skill.strip().lower() for skill in 
                                self.config['Skills']['required'].split(','))
            preferred_skills = set(skill.strip().lower() for skill in 
                                 self.config['Skills']['preferred'].split(','))
            
            job_description = job_description.lower()
            
            # Check required skills
            missing_required = [skill for skill in required_skills 
                              if skill not in job_description]
            if missing_required:
                self.logger.debug(f"Missing required skills: {missing_required}")
                return False
            
            # Count preferred skills
            matched_preferred = [skill for skill in preferred_skills 
                               if skill in job_description]
            min_preferred = int(self.config['Skills'].get('min_preferred', 1))
            
            return len(matched_preferred) >= min_preferred
            
        except Exception as e:
            self.logger.error(f"Error filtering job posting: {str(e)}")
            return False

    def save_application_data(self) -> None:
        """Save application data to JSON file."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'applications_submitted': self.applications_submitted,
            'jobs_processed': self.jobs_processed,
            'search_results': self.search_results
        }
        
        filename = f'application_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        self.logger.info(f"Application data saved to {filename}")

    def quit(self) -> None:
        """Clean up resources and save final data."""
        try:
            self.save_application_data()
            if hasattr(self, 'driver'):
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()

# test_job_bot.py
import unittest
from unittest.mock import Mock, patch
from main import JobApplicationBot
import os

class TestJobApplicationBot(unittest.TestCase):
    def setUp(self):
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
            ''')
    
    def tearDown(self):
        # Clean up test config
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
    
    @patch('selenium.webdriver.Chrome')
    def test_initialization(self, mock_chrome):
        bot = JobApplicationBot(config_path=self.test_config)
        self.assertIsNotNone(bot.config)
        self.assertEqual(bot.applications_submitted, 0)
        self.assertEqual(bot.jobs_processed, 0)
    
    @patch('selenium.webdriver.Chrome')
    def test_login_to_portal(self, mock_chrome):
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Mock the WebDriver wait and element
        mock_element = Mock()
        mock_chrome.return_value.find_element.return_value = mock_element
        
        result = bot.login_to_portal('LinkedIn')
        self.assertTrue(result)
    
    @patch('selenium.webdriver.Chrome')
    def test_filter_job_posting(self, mock_chrome):
        bot = JobApplicationBot(config_path=self.test_config)
        
        # Test with matching required and preferred skills
        job_description = "We're looking for a Python developer with Selenium and JavaScript experience"
        self.assertTrue(bot.filter_job_posting(job_description))
        
        # Test with missing required skills
        job_description = "We're looking for a JavaScript developer with Docker experience"
        self.assertFalse(bot.filter_job_posting(job_description))

if __name__ == '__main__':
    unittest.main()