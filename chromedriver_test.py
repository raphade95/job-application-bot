from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import sys
import platform

def check_chrome_setup():
    print("System Information:")
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.machine()}")
    
    try:
        # Initialize the Chrome driver with automatic ChromeDriver management
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        
        # Get Chrome and ChromeDriver versions
        chrome_version = driver.capabilities['browserVersion']
        chromedriver_version = driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
        
        print("\nVersion Information:")
        print(f"Chrome Version: {chrome_version}")
        print(f"ChromeDriver Version: {chromedriver_version}")
        
        # Try to load a page to verify everything works
        print("\nTesting page load...")
        driver.get("https://www.google.com")
        
        # Try to find an element to verify Selenium commands work
        search_box = driver.find_element(By.NAME, "q")
        print("Successfully found search box element")
        
        print("\nAll checks passed! ChromeDriver is working correctly.")
        
    except Exception as e:
        print(f"\nError encountered: {str(e)}")
        return False
    finally:
        if 'driver' in locals():
            driver.quit()
    
    return True

if __name__ == "__main__":
    check_chrome_setup()