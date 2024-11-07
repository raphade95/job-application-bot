# run_bot.py
from main import JobApplicationBot
import logging
import argparse
from typing import Dict
import json

def load_search_config(config_file: str = 'search_config.json') -> Dict:
    """Load search configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "searches": [
                {
                    "keywords": "Python Developer",
                    "location": "Remote",
                    "filters": None
                },
                {
                    "keywords": "Software Engineer",
                    "location": "San Francisco",
                    "filters": {
                        "experience_level": "Entry level",
                        "job_type": "Full-time",
                        "remote": "Remote",
                        "date_posted": "Past 24 hours"
                    }
                }
            ]
        }

def run_job_search():
    """Execute job searches based on configuration"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load search configuration
    search_config = load_search_config()
    
    try:
        with JobApplicationBot() as bot:
            # Attempt to login
            if not bot.login_to_linkedin():
                logger.error("Failed to login to LinkedIn")
                return
            
            logger.info("Successfully logged in to LinkedIn")
            
            # Execute each search from the configuration
            for search in search_config["searches"]:
                try:
                    logger.info(f"Starting search for {search['keywords']} in {search['location']}")
                    
                    success = bot.search_linkedin_jobs(
                        keywords=search["keywords"],
                        location=search["location"],
                        filters=search["filters"]
                    )
                    
                    if success:
                        logger.info(f"Successfully completed search for {search['keywords']}")
                    else:
                        logger.error(f"Failed to complete search for {search['keywords']}")
                        
                except Exception as e:
                    logger.error(f"Error during search for {search['keywords']}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Bot execution failed: {str(e)}")

if __name__ == "__main__":
    run_job_search()