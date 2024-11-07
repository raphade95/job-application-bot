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
from typing import Optional, Dict, List, Tuple
import atexit
from selenium.webdriver.support.ui import Select

class JobApplicationBot:
    def __init__(self, config_path: str = 'config.ini'):
        """Initialize the job application bot with enhanced logging and configuration."""
        self._setup_logging()
        self.config = self._load_config(config_path)
        self.applications_submitted = 0
        self.jobs_processed = 0
        self.search_results = []
        self._setup_webdriver()
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
    def _setup_logging(self) -> None:
        """Set up enhanced logging with both file and console output."""
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(
            log_dir, 
            f'job_applications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        
        # Create a logger instance instead of using basicConfig
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create handlers
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler()
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Store handlers for cleanup
        self.handlers = [file_handler, console_handler]
        
    def cleanup(self) -> None:
        """Cleanup resources properly."""
        # Close logging handlers
        for handler in self.handlers:
            handler.close()
            self.logger.removeHandler(handler)
        
        # Save any pending data
        self.save_application_data()
        
        # Quit WebDriver if it exists
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load and validate configuration from INI file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        config = configparser.ConfigParser()
        config.read(config_path)
        
        required_sections = ['LinkedIn', 'Skills', 'SearchCriteria']
        missing_sections = [section for section in required_sections if section not in config]
        if missing_sections:
            raise ValueError(f"Missing required configuration sections: {', '.join(missing_sections)}")
                
        return config
    
    def _setup_webdriver(self) -> None:
        """Initialize Chrome WebDriver with enhanced options."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-notifications')
            
            if self.config.has_section('BrowserOptions'):
                for option in self.config['BrowserOptions']:
                    options.add_argument(option)
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def take_screenshot(self, name: str) -> Optional[str]:
        """Take a screenshot and save it to the logs directory."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/screenshot_{name}_{timestamp}.png"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.driver.save_screenshot(filename)
            self.logger.info(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {str(e)}")
            return None

    def check_for_captcha(self) -> Tuple[bool, str]:
        """
        Check if a CAPTCHA is present on the page.
        Returns a tuple of (is_captcha_present, captcha_type)
        """
        try:
            captcha_indicators = {
                'reCAPTCHA': "//iframe[contains(@src, 'recaptcha')]",
                'hCaptcha': "//iframe[contains(@src, 'hcaptcha')]",
                'Generic': "//*[contains(text(), 'Captcha') or contains(text(), 'Security Check')]"
            }
            
            for captcha_type, xpath in captcha_indicators.items():
                if len(self.driver.find_elements(By.XPATH, xpath)) > 0:
                    self.logger.warning(f"{captcha_type} detected!")
                    screenshot_path = self.take_screenshot(f"{captcha_type.lower()}_detected")
                    return True, captcha_type
                    
            return False, ""
            
        except Exception as e:
            self.logger.error(f"Error checking for CAPTCHA: {str(e)}")
            return False, ""

    def handle_timeout(self, action: str, retry_count: int = 3, wait_time: int = 30) -> bool:
        """
        Handle timeout situations with retries and CAPTCHA detection.
        
        Args:
            action: Description of the action being attempted
            retry_count: Number of retry attempts
            wait_time: Time to wait for manual intervention (seconds)
        
        Returns:
            bool: True if action succeeded, False otherwise
        """
        for attempt in range(retry_count):
            try:
                is_captcha, captcha_type = self.check_for_captcha()
                
                if is_captcha:
                    self.logger.warning(
                        f"{captcha_type} detected during {action}. "
                        f"Waiting {wait_time} seconds for manual intervention."
                    )
                    
                    # Take screenshot for debugging
                    self.take_screenshot(f"{action}_captcha_attempt_{attempt}")
                    
                    # Wait for manual intervention
                    time.sleep(wait_time)
                    
                    # Check if CAPTCHA is still present
                    is_captcha, _ = self.check_for_captcha()
                    if not is_captcha:
                        self.logger.info("CAPTCHA appears to be solved, continuing...")
                        return True
                        
                else:
                    self.logger.info(f"Retrying {action} (attempt {attempt + 1}/{retry_count})")
                    # Exponential backoff
                    retry_delay = 2 ** attempt
                    time.sleep(retry_delay)
                    return True
                    
            except Exception as e:
                self.logger.error(f"Error during {action} retry: {str(e)}")
                if attempt == retry_count - 1:
                    return False
                    
        return False

    def wait_for_element(self, by: By, value: str, timeout: int = 10, 
                    clickable: bool = False, retries: int = 3) -> Optional[webdriver.remote.webelement.WebElement]:
        """Wait for an element to be present or clickable with retry logic and CAPTCHA handling."""
        for attempt in range(retries):
            try:
                condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
                return self.wait.until(condition((by, value)))
                    
            except TimeoutException:
                is_captcha, captcha_type = self.check_for_captcha()
                if is_captcha:
                    self.logger.warning(
                        f"CAPTCHA detected while waiting for element {value}. "
                        "Waiting for manual intervention..."
                    )
                    if self.handle_timeout(f"waiting for element {value}"):
                        continue
                        
                self.logger.warning(f"Timeout waiting for element: {value} (attempt {attempt + 1}/{retries})")
                if attempt == retries - 1:
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error waiting for element {value}: {str(e)}")
                return None

    def save_application_data(self) -> None:
        """Save application data to JSON file with error handling."""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'applications_submitted': self.applications_submitted,
                'jobs_processed': self.jobs_processed,
                'search_results': self.search_results
            }
            
            # Ensure the directory exists
            os.makedirs('data', exist_ok=True)
            
            filename = os.path.join('data', f'application_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.logger.info(f"Application data saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save application data: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.cleanup()
        if exc_val:
            self.logger.error(f"Error during execution: {str(exc_val)}")
            return False
        
    def login_to_linkedin(self) -> bool:
        """Login to LinkedIn with error handling and verification."""
        try:
            self.logger.info("Attempting to login to LinkedIn...")
            self.driver.get(self.config['LinkedIn']['login_url'])
            
            # Wait for and enter email
            email_field = self.wait_for_element(
                By.ID, "username", 
                clickable=True
            )
            if not email_field:
                self.logger.error("Could not find email field")
                return False
                
            email_field.send_keys(self.config['LinkedIn']['email'])
            
            # Wait for and enter password
            password_field = self.wait_for_element(
                By.ID, "password", 
                clickable=True
            )
            if not password_field:
                self.logger.error("Could not find password field")
                return False
                
            password_field.send_keys(self.config['LinkedIn']['password'])
            
            # Click sign in button
            sign_in_button = self.wait_for_element(
                By.CSS_SELECTOR, "button[type='submit']", 
                clickable=True
            )
            if not sign_in_button:
                self.logger.error("Could not find sign in button")
                return False
                
            sign_in_button.click()
            
            # Verify successful login by checking for nav bar
            nav_bar = self.wait_for_element(
                By.CSS_SELECTOR, 
                ".global-nav__nav"
            )
            if not nav_bar:
                self.logger.error("Login verification failed")
                return False
            
            self.logger.info("Successfully logged into LinkedIn")
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def search_linkedin_jobs(self, keywords: str, location: str = None, 
                           filters: Dict[str, str] = None) -> bool:
        """
        Search for jobs on LinkedIn with specified criteria.
        
        Args:
            keywords: Job search keywords
            location: Optional location filter
            filters: Optional dictionary of additional filters
                    e.g. {"experience_level": "Entry level",
                          "job_type": "Full-time",
                          "remote": "Remote"}
        """
        try:
            # Navigate to LinkedIn Jobs
            self.driver.get("https://www.linkedin.com/jobs/")
            
            # Wait for search box
            search_box = self.wait_for_element(
                By.CSS_SELECTOR, 
                "input.jobs-search-box__text-input[aria-label='Search by title, skill, or company']",
                clickable=True
            )
            if not search_box:
                self.logger.error("Could not find job search box")
                return False
                
            # Clear and enter keywords
            search_box.clear()
            search_box.send_keys(keywords)
            
            # Handle location if provided
            if location:
                location_box = self.wait_for_element(
                    By.CSS_SELECTOR,
                    "input.jobs-search-box__text-input[aria-label='City, state, or zip code']",
                    clickable=True
                )
                if location_box:
                    location_box.clear()
                    location_box.send_keys(location)
            
            # Apply additional filters if provided
            if filters:
                self._apply_linkedin_filters(filters)
            
            # Submit search
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results
            results = self.wait_for_element(
                By.CLASS_NAME, "jobs-search__results-list"
            )
            if not results:
                self.logger.error("No job results found")
                return False
            
            self.logger.info(f"Successfully searched for {keywords} jobs")
            return True
            
        except Exception as e:
            self.logger.error(f"Job search failed: {str(e)}")
            return False

    def _apply_linkedin_filters(self, filters: Dict[str, str]) -> None:
        """Apply job search filters on LinkedIn."""
        try:
            # Click "All filters" button
            all_filters_button = self.wait_for_element(
                By.CSS_SELECTOR,
                "button[aria-label='All filters']",
                clickable=True
            )
            if all_filters_button:
                all_filters_button.click()
                time.sleep(1)  # Wait for filter modal
                
                # Map of filter types to their selectors
                filter_selectors = {
                    "experience_level": "Experience level",
                    "job_type": "Job Type",
                    "remote": "Remote",
                    "salary": "Salary",
                    "date_posted": "Date posted"
                }
                
                for filter_type, value in filters.items():
                    if filter_type in filter_selectors:
                        filter_name = filter_selectors[filter_type]
                        self._select_linkedin_filter(filter_name, value)
                
                # Apply filters
                apply_button = self.wait_for_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Apply current filters']",
                    clickable=True
                )
                if apply_button:
                    apply_button.click()
                    time.sleep(1)  # Wait for filters to apply
                    
        except Exception as e:
            self.logger.error(f"Error applying filters: {str(e)}")

    def _select_linkedin_filter(self, filter_name: str, value: str) -> None:
        """Select a specific filter value in the LinkedIn filter modal."""
        try:
            # Find and click the filter section
            filter_button = self.wait_for_element(
                By.XPATH,
                f"//button[contains(text(), '{filter_name}')]",
                clickable=True
            )
            if filter_button:
                filter_button.click()
                time.sleep(0.5)
                
                # Find and click the specific value
                value_element = self.wait_for_element(
                    By.XPATH,
                    f"//label[contains(text(), '{value}')]",
                    clickable=True
                )
                if value_element:
                    value_element.click()
                    
        except Exception as e:
            self.logger.error(f"Error selecting filter {filter_name}: {str(e)}")

if __name__ == "__main__":
    with JobApplicationBot() as bot:
        # Example usage
        if bot.login_to_portal('LinkedIn'):
            bot.search_jobs("Python Developer", "Remote")