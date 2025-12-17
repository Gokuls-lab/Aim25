import time
import shutil
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

class ResearchBrowser:
    def __init__(self):
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """Sets up a detached Brave browser instance."""
        temp_profile = "/tmp/Atlas_Browser_Profile"
        
        if os.path.exists(temp_profile):
            try: shutil.rmtree(temp_profile)
            except: pass
            
        try:
            shutil.copytree(
                config.USER_DATA_DIR, 
                temp_profile, 
                ignore=shutil.ignore_patterns("Cache*", "Code Cache*", "Singleton*", "lock")
            )
        except: pass

        options = Options()
        options.binary_location = config.BRAVE_PATH
        options.add_argument(f"--user-data-dir={temp_profile}")
        options.add_argument(f"--profile-directory={config.PROFILE_DIR}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # VISIBILITY: Keep this visible to debug/bypass captchas
        options.add_argument("--start-maximized")
        
        try:
            driver_path = ChromeDriverManager(driver_version="143").install()
            service = Service(driver_path)
        except:
            service = Service()

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30) # Increase timeout
        return driver

    def search_google(self, query):
        """
        Performs Google search and returns:
        1. The text of the Google Page (AI Overview, Snippets)
        2. Top 3 URLs to surf
        """
        print(f"🔎 Googling: '{query}'...")
        try:
            self.driver.get("https://www.google.com")
            
            # 1. Handle Search Box (Wait up to 10s)
            try:
                wait = WebDriverWait(self.driver, 10)
                box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
            except:
                # Fallback: Sometimes Google shows a privacy/cookie banner blocking interaction
                print("⚠️ Search box not found. Checking for popups...")
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                return body_text, []

            box.clear()
            box.send_keys(query)
            box.send_keys(Keys.RETURN)
            
            # 2. Wait for Results (Look for 'search' ID or standard result class)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "search")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
                    )
                )
            except:
                print("⚠️ Timeout waiting for results. Returning current page text.")
            
            # 3. Capture Google AI/Snippet Text
            time.sleep(2) # Brief pause for JS rendering
            serp_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # 4. Extract Links (Surfing Targets)
            results = []
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g a h3")
            
            for el in elements[:3]: 
                try:
                    parent = el.find_element(By.XPATH, "./../..")
                    link = parent.get_attribute("href")
                    if link and "google.com" not in link:
                        results.append(link)
                except: continue
            
            return serp_text, results

        except Exception as e:
            print(f"❌ Search Error: {e}")
            return "", []

    def scrape_text(self, url):
        """Surfs to a URL and reads content."""
        print(f"📄 Surfing: {url}")
        try:
            self.driver.get(url)
            
            # Wait for content
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Remove scripts/styles for cleaner text
            self.driver.execute_script("""
                var elements = document.getElementsByTagName('script');
                while (elements[0]) elements[0].parentNode.removeChild(elements[0]);
                var elements = document.getElementsByTagName('style');
                while (elements[0]) elements[0].parentNode.removeChild(elements[0]);
            """)
            
            body = self.driver.find_element(By.TAG_NAME, "body").text
            return " ".join(body.split())[:12000] 
        except Exception as e:
            print(f"⚠️ Surf Error ({url}): {e}")
            return ""

    def close(self):
        self.driver.quit()