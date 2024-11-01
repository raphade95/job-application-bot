import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import configparser

class IndeedJobBot:
    def __init__(self, config_path='config.ini'):
        # Set up logging
        logging.basicConfig(
            filename=f'indeed_applications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize Chrome options
        chrome_options = webdriver.ChromeOptions()
        if self.config.getboolean('Browser', 'headless', fallback=False):
            chrome_options.add_argument('--headless')
        
        # Initialize the webdriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.driver.maximize_window()
        
        # Initialize results tracking
        self.applications_submitted = 0
        self.jobs_processed = 0
        
    def _load_config(self, config_path):
        """Load configuration from INI file"""
        config = configparser.ConfigParser()
        config.read(config_path)
        return config

    def login_to_indeed(self):
        """Login to Indeed"""
        try:
            self.driver.get("https://secure.indeed.com/auth")
            
            # Wait for and enter email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ifl-InputFormField-3"))
            )
            email_field.send_keys(self.config['Indeed']['email'])
            
            # Click continue button
            continue_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_button.click()
            
            # Wait for and enter password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ifl-InputFormField-7"))
            )
            password_field.send_keys(self.config['Indeed']['password'])
            
            # Click sign in button
            sign_in_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
            sign_in_button.click()
            
            time.sleep(3)  # Wait for login to complete
            logging.info("Successfully logged into Indeed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to login to Indeed: {str(e)}")
            return False

    def search_jobs(self, keywords, location=None):
        """Search for jobs based on keywords and location"""
        try:
            # Navigate to Indeed search page
            self.driver.get("https://www.indeed.com")
            
            # Enter keywords
            what_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "text-input-what"))
            )
            what_field.clear()
            what_field.send_keys(keywords)
            
            # Enter location if provided
            if location:
                where_field = self.driver.find_element(By.ID, "text-input-where")
                where_field.clear()
                where_field.send_keys(location)
            
            # Click search button
            search_button = self.driver.find_element(By.CLASS_NAME, "yosegi-InlineWhatWhere-primaryButton")
            search_button.click()
            
            logging.info(f"Performed job search for '{keywords}' in {location if location else 'any location'}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to perform job search: {str(e)}")
            return False

    def filter_job_posting(self, job_description):
        """Filter job posting based on requirements and keywords"""
        required_skills = set(self.config['Skills']['required'].split(','))
        preferred_skills = set(self.config['Skills']['preferred'].split(','))
        
        # Convert job description to lowercase for case-insensitive matching
        job_description = job_description.lower()
        
        # Check if all required skills are present
        if not all(skill.lower() in job_description for skill in required_skills):
            return False
        
        # Count preferred skills
        preferred_matches = sum(1 for skill in preferred_skills 
                              if skill.lower() in job_description)
        
        # Return True if enough preferred skills are present
        min_preferred = int(self.config['Skills']['min_preferred'])
        return preferred_matches >= min_preferred

    def apply_to_job(self, job_card):
        """Apply to a specific job"""
        try:
            # Click on job card to view details
            job_card.click()
            time.sleep(2)
            
            # Get job description
            job_description = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobsearch-JobComponent-description"))
            ).text
            
            # Check if job matches criteria
            if not self.filter_job_posting(job_description):
                logging.info("Job doesn't match required criteria")
                return False
            
            # Click apply button
            apply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "jobsearch-IndeedApplyButton-newDesign"))
            )
            apply_button.click()
            
            # Handle Indeed Easy Apply form
            self._handle_indeed_apply_form()
            
            self.applications_submitted += 1
            logging.info("Successfully applied to job")
            return True
            
        except Exception as e:
            logging.error(f"Failed to apply to job: {str(e)}")
            return False

    def _handle_indeed_apply_form(self):
        """Handle Indeed's Easy Apply form"""
        try:
            # Switch to the application iframe
            iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "indeed-apply-iframe"))
            )
            self.driver.switch_to.frame(iframe)
            
            # Handle each step of the application
            while True:
                # Look for continue button
                try:
                    continue_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Submit')]"))
                    )
                    continue_button.click()
                    time.sleep(1)
                except TimeoutException:
                    break
            
            # Switch back to main content
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logging.error(f"Error handling application form: {str(e)}")
            self.driver.switch_to.default_content()

    def run_job_search_campaign(self, keywords, location=None, max_applications=50):
        """Run a complete job application campaign"""
        try:
            if not self.login_to_indeed():
                return False
            
            if not self.search_jobs(keywords, location):
                return False
            
            while self.applications_submitted < max_applications:
                # Get list of job results
                job_cards = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CLASS_NAME, "job_seen_beacon")
                    )
                )
                
                for job_card in job_cards:
                    if self.applications_submitted >= max_applications:
                        break
                    
                    self.jobs_processed += 1
                    self.apply_to_job(job_card)
                    time.sleep(2)
                
                # Try to click next page
                try:
                    next_button = self.driver.find_element(By.XPATH, "//a[contains(@aria-label, 'Next')]")
                    if not next_button.is_enabled():
                        break
                    next_button.click()
                    time.sleep(2)
                except NoSuchElementException:
                    break
            
            logging.info(f"""Campaign completed:
                        Jobs processed: {self.jobs_processed}
                        Applications submitted: {self.applications_submitted}""")
            
        finally:
            self.driver.quit()
            
    def generate_report(self):
        """Generate a report of the job application campaign"""
        report_path = f'indeed_application_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(report_path, 'w') as f:
            f.write(f"Indeed Job Application Report\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Jobs Processed: {self.jobs_processed}\n")
            f.write(f"Applications Submitted: {self.applications_submitted}\n")
            
        logging.info(f"Report generated: {report_path}")