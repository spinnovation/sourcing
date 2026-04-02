import time
import urllib.parse
from playwright.sync_api import sync_playwright

def dump_mobile():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            viewport={'width': 390, 'height': 844},
            is_mobile=True,
            has_touch=True
        )
        page = context.new_page()
        kw = urllib.parse.quote('유모차')
        url = f'https://m.shopping.naver.com/search/all?query={kw}'
        
        page.goto(url, wait_until='networkidle')
        time.sleep(3)
        
        with open('mobile_dump.html', 'w', encoding='utf-8') as f:
            f.write(page.content())
            
        print("Mobile dump complete.")
        browser.close()

if __name__ == "__main__":
    dump_mobile()
