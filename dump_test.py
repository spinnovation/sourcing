import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
# options.add_argument("--headless=new") # Let's try headless first
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
url = "https://search.shopping.naver.com/search/all?query=" + urllib.parse.quote("유모차") + "&pagingIndex=1&pagingSize=80"
driver.get(url)
time.sleep(3)

with open("naver_dump.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

driver.quit()
print("Dump completed.")
