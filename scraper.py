import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time

# Config
BASE_URL = "https://exhibitors.gulfood.com/gulfood-2026/Exhibitor"
OUTPUT_DIR = "data"
CSV_FILE = os.path.join(OUTPUT_DIR, "exhibitors.csv")
JSON_FILE = os.path.join(OUTPUT_DIR, "exhibitors.json")
MAX_SCROLL_ATTEMPTS = 100 
SCROLL_PAUSE_TIME = 2 

async def scrape_gulfood():
    start_time = time.time()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {BASE_URL}...")
        try:
            await page.goto(BASE_URL, timeout=60000)
            print("Page loaded.")
        except Exception as e:
            print(f"Error loading page: {e}")
            await browser.close()
            return
        
        # Scroll down to load everything
        print("Starting infinite scroll to load all exhibitors...")
        last_height = await page.evaluate("document.body.scrollHeight")
        scroll_attempts = 0
        no_change_count = 0
        
        while scroll_attempts < MAX_SCROLL_ATTEMPTS:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(SCROLL_PAUSE_TIME * 1000)
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    print("No new content loaded for 3 consecutive attempts. Stopping scroll.")
                    break
            else:
                no_change_count = 0
                last_height = new_height
            
            scroll_attempts += 1
            print(f"Scroll {scroll_attempts} complete. Current height: {new_height}")

        # Get all the profile links
        print("Extracting detail page URLs...")
        detail_links = await page.locator("a.btn").all()
        
        urls = []
        for link in detail_links:
            text = await link.text_content()
            href = await link.get_attribute("href")
            if href and "VIEW PROFILE" in text.upper():
                full_url = href if href.startswith("http") else f"https://exhibitors.gulfood.com{href}"
                urls.append(full_url)
        
        # Dedup URLs but keep the order
        seen = set()
        urls = [x for x in urls if not (x in seen or seen.add(x))]
        print(f"Found {len(urls)} unique exhibitor URLs.")

        # Go through each one and grab the info
        exhibitors_data = []
        
        for i, url in enumerate(urls):
            print(f"Scraping {i+1}/{len(urls)}: {url}")
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")
                
                # Init data dict
                data = {
                    "url": url,
                    "name": "",
                    "country": "",
                    "stand": "",
                    "website": "",
                    "description": "",
                    "categories": [],
                    "social_facebook": "",
                    "social_linkedin": "",
                    "social_instagram": "",
                    "social_youtube": "",
                    "social_twitter": ""
                }
                
                # Parse the messy text content
                body_text = await page.locator("body").inner_text()
                lines = [line.strip() for line in body_text.split('\n') if line.strip()]
                
                # Name usually comes after this line
                try:
                    idx = -1
                    for i, line in enumerate(lines):
                        if "BACK TO EXHIBITOR LIST" in line.upper():
                            idx = i
                            break
                    if idx != -1 and idx + 1 < len(lines):
                        data["name"] = lines[idx + 1]
                except Exception:
                    pass

                # Stand & Country
                stand_idx = -1
                for i, line in enumerate(lines):
                    if line.startswith("Stand No"):
                        data["stand"] = line
                        stand_idx = i
                        if i + 1 < len(lines):
                            data["country"] = lines[i+1]
                        break
                
                # Use "VISIT WEBSITE" as a delimiter
                visit_website_idx = -1
                for i, line in enumerate(lines):
                    if "VISIT WEBSITE" in line:
                        visit_website_idx = i
                        break
                
                # Description & Categories
                profile_idx = -1
                for i, line in enumerate(lines):
                    if "COMPANY PROFILE" in line.upper():
                        profile_idx = i
                        break
                
                categories_start_idx = -1
                
                if profile_idx != -1:
                    # Description is right after the header
                    if profile_idx + 1 < len(lines):
                        data["description"] = lines[profile_idx + 1]
                        categories_start_idx = profile_idx + 2
                else:
                    # No profile header? Categories might start after Country
                    if stand_idx != -1:
                        categories_start_idx = stand_idx + 2
                
                # Grab categories
                if categories_start_idx != -1 and visit_website_idx != -1:
                    if categories_start_idx < visit_website_idx:
                        cats = lines[categories_start_idx : visit_website_idx]
                        # Filter out UI noise
                        clean_cats = [c for c in cats if c not in ["BROCHURES", "VIDEOS", "IMAGE PDF DOWNLOAD PDF", "Find us on:"]]
                        data["categories"] = clean_cats

                # Website
                website_el = page.locator("a:has-text('VISIT WEBSITE')")
                if await website_el.count() > 0:
                    data["website"] = await website_el.get_attribute("href")

                # Social links
                if await page.locator(".fb_link").count() > 0:
                    data["social_facebook"] = await page.locator(".fb_link").get_attribute("href")
                if await page.locator(".linkdin_link").count() > 0:
                    data["social_linkedin"] = await page.locator(".linkdin_link").get_attribute("href")
                if await page.locator(".insta_link").count() > 0:
                    data["social_instagram"] = await page.locator(".insta_link").get_attribute("href")
                if await page.locator(".youtube_link").count() > 0:
                    data["social_youtube"] = await page.locator(".youtube_link").get_attribute("href")
                if await page.locator(".twitter_link").count() > 0:
                    data["social_twitter"] = await page.locator(".twitter_link").get_attribute("href")
                
                exhibitors_data.append(data)
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        # Save it
        print(f"Saving {len(exhibitors_data)} exhibitors to files...")
        df = pd.DataFrame(exhibitors_data)
        df.to_csv(CSV_FILE, index=False)
        
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(exhibitors_data, f, indent=4, ensure_ascii=False)
            
        print(f"Data saved to:\n- {os.path.abspath(CSV_FILE)}\n- {os.path.abspath(JSON_FILE)}")

        await browser.close()
        
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Scraping completed in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(scrape_gulfood())
