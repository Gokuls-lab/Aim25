import time
import shutil
import os
import random
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
        if os.path.exists(config.BRAVE_PATH):
             options.binary_location = config.BRAVE_PATH

        options.add_argument(f"--user-data-dir={temp_profile}")
        options.add_argument(f"--profile-directory={config.PROFILE_DIR}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--start-maximized")

        # STRATEGY 1: Selenium Manager (Best for modern setups)
        try:
            print("🌐 Attempting to launch browser with Selenium Manager...")
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(45)
            print("✅ Browser Launched via Selenium Manager")
            return driver
        except Exception as e:
            print(f"⚠️ Selenium Manager failed: {e}. Trying webdriver_manager...")

        # STRATEGY 2: Fallbacks
        try:
            service = Service(ChromeDriverManager(driver_version="131.0.6778.204").install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(45) 
            return driver
        except Exception as e:
            print(f"❌ Critical Browser Failure: {e}")
            raise e

    def check_and_solve_captcha(self):
        """
        Attempts to auto-click 'I'm not a robot' checkboxes.
        """
        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                try:
                    src = frame.get_attribute("src")
                    if src and ("recaptcha" in src or "captcha" in src):
                        self.driver.switch_to.frame(frame)
                        try:
                            checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                            checkbox.click()
                            print("🤖 Auto-clicked CAPTCHA!")
                            time.sleep(2)
                        except: pass
                        self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
            
            buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'human') or contains(text(), 'verify')]")
            for btn in buttons:
                try:
                    btn.click()
                    print("🤖 Auto-clicked Verification Button!")
                    time.sleep(2)
                except: pass
        except Exception:
            pass
        return False

    def search_google(self, query):
        print(f"G-Search: '{query}'")
        try:
            self.driver.get("https://www.google.com")
            try:
                wait = WebDriverWait(self.driver, 5)
                box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
            except:
                self.check_and_solve_captcha()
                try: box = self.driver.find_element(By.NAME, "q")
                except: return "", []

            box.clear()
            box.send_keys(query)
            box.send_keys(Keys.RETURN)
            self.check_and_solve_captcha()
            
            try:
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.g")))
            except: pass
            
            time.sleep(1) 
            serp_text = self.driver.find_element(By.TAG_NAME, "body").text
            results = []
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g a h3")
            for el in elements[:4]: 
                try:
                    parent = el.find_element(By.XPATH, "./../..")
                    link = parent.get_attribute("href")
                    if link and "google.com" not in link: results.append(link)
                except: continue
            return serp_text, results
        except Exception as e:
            print(f"❌ Google Error: {e}")
            return "", []

    def search_duckduckgo(self, query):
        print(f"D-Search: '{query}'")
        try:
            self.driver.get("https://duckduckgo.com")
            self.check_and_solve_captcha()
            try:
                wait = WebDriverWait(self.driver, 5)
                box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
            except: 
                try: box = self.driver.find_element(By.NAME, "q")
                except: return "", []

            box.clear()
            box.send_keys(query)
            box.send_keys(Keys.RETURN)
            self.check_and_solve_captcha()
            time.sleep(2)
            
            try:
                # Optimized for DuckDuckGo's dynamic loading
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='result-title-a']"))
                )
            except: pass
            
            serp_text = self.driver.find_element(By.TAG_NAME, "body").text
            results = []
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
            for el in elements[:4]:
                try:
                    link = el.get_attribute("href")
                    if link: results.append(link)
                except: continue
            return serp_text, results
        except Exception as e:
             # Fallback if selectors change
            print(f"❌ DDG Error: {e}")
            return "", []

    def open_new_tab(self, url="about:blank"):
        self.driver.execute_script(f"window.open('{url}');")
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def switch_to_tab(self, tab_index):
        if tab_index < len(self.driver.window_handles):
            self.driver.switch_to.window(self.driver.window_handles[tab_index])

    def close_current_tab(self):
         if len(self.driver.window_handles) > 1:
             self.driver.close()
             self.driver.switch_to.window(self.driver.window_handles[-1])

    # === NEW: Parallel Tab Management Methods ===
    
    def get_tab_count(self):
        """Returns the number of currently open tabs."""
        return len(self.driver.window_handles)
    
    def get_all_tab_handles(self):
        """Returns list of all tab handles."""
        return self.driver.window_handles
    
    def switch_to_tab_by_handle(self, handle):
        """Switch to a specific tab by its handle."""
        try:
            self.driver.switch_to.window(handle)
            return True
        except:
            return False
    
    def open_url_in_new_tab(self, url):
        """Opens a URL in a new tab and switches to it."""
        self.driver.execute_script(f"window.open('{url}', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        return self.driver.window_handles[-1]
    
    def close_all_extra_tabs(self):
        """Closes all tabs except the first one."""
        while len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
    
    def execute_search_url(self, engine, query):
        """
        Navigate to search URL directly (faster than typing).
        Returns current page handle.
        """
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        
        if engine == "google":
            url = f"https://www.google.com/search?q={encoded_query}"
        else:  # duckduckgo
            url = f"https://duckduckgo.com/?q={encoded_query}"
        
        try:
            self.driver.get(url)
            return self.driver.current_window_handle
        except Exception as e:
            print(f"⚠️ Search URL error: {e}")
            return None

    def extract_logo(self, domain):
        url = f"https://{domain}" if not domain.startswith("http") else domain
        print(f"🖼️  Hunting for logo on: {url}")
        try:
            self.driver.get(url)
            try: WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except: pass
            
            try:
                og_img = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]').get_attribute("content")
                if og_img: return og_img
            except: pass
            return ""
        except: return ""

    def scrape_text(self, url):
        print(f"📄 Surfing: {url}")
        try:
            self.driver.get(url)
            self.check_and_solve_captcha()
            try: WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except: pass
            
            try:
                self.driver.execute_script("""
                    var elements = document.getElementsByTagName('script');
                    while (elements[0]) elements[0].parentNode.removeChild(elements[0]);
                """)
            except: pass
            
            body = self.driver.find_element(By.TAG_NAME, "body").text
            return f"CONTENT:\n{' '.join(body.split())[:15000]}"
        except: return ""

    def close(self):
        try: self.driver.quit()
        except: pass