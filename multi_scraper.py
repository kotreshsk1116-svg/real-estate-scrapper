import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def scrape_magicbricks(page):
    print("Scraping MagicBricks...")
    # NMIT is in Yelahanka, Bangalore
    url = "https://www.magicbricks.com/property-for-rent/residential-real-estate?bedroom=1,2,3&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment&Locality=Yelahanka&cityName=Bangalore"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Give JS time to fetch and render the properties
        await page.wait_for_timeout(5000)
        
        listings = await page.locator('.mb-srp__card').all()
        print(f"MagicBricks found {len(listings)} listings")
        
        results = []
        for listing in listings[:5]: # Take top 5 for V1 demonstration
            try:
                title = await listing.locator('.mb-srp__card--title').inner_text()
                rent = await listing.locator('.mb-srp__card__price--amount').inner_text()
                results.append({
                    "source": "MagicBricks",
                    "title": title.strip(),
                    "rent": rent.strip(),
                    "url": url
                })
            except Exception as e:
                pass
        return results
    except Exception as e:
        print(f"MagicBricks failed: {e}")
        return []

async def scrape_twitter(page):
    print("Scraping Twitter...")
    # Trying public search (often blocks without login, but we'll try)
    url = "https://twitter.com/search?q=rent%20(Yelahanka%20OR%20NMIT)&src=typed_query&f=live"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        
        results = []
        tweets = await page.locator('[data-testid="tweet"]').all()
        print(f"Twitter found {len(tweets)} tweets")
        for tweet in tweets[:5]:
            text = await tweet.locator('[data-testid="tweetText"]').inner_text()
            results.append({
                "source": "Twitter",
                "text": text.strip(),
                "url": url
            })
        return results
    except Exception as e:
        print("Twitter scraping failed (likely blocked by login wall):", e)
        return []

async def scrape_facebook(page):
    print("Scraping Facebook...")
    # Trying public search (Facebook aggressively requires login for search)
    url = "https://www.facebook.com/search/posts/?q=rent%20flat%20Yelahanka%20Bangalore"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        
        results = []
        # Fallback to generic article roles if classes are dynamic
        posts = await page.locator('div[role="article"]').all()
        print(f"Facebook found {len(posts)} posts")
        for post in posts[:5]:
            text = await post.inner_text()
            results.append({
                "source": "Facebook",
                "text": text[:200] + "...",
                "url": url
            })
        return results
    except Exception as e:
        print("Facebook scraping failed (likely blocked by login wall):", e)
        return []

async def main():
    print("Starting Multi-Scraper for NMIT / Yelahanka (5km radius)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        all_results = []
        
        # 1. MagicBricks
        mb_data = await scrape_magicbricks(page)
        all_results.extend(mb_data)
            
        # 2. Twitter
        tw_data = await scrape_twitter(page)
        all_results.extend(tw_data)
            
        # 3. Facebook
        fb_data = await scrape_facebook(page)
        all_results.extend(fb_data)
            
        with open("v1_results.json", "w") as f:
            json.dump(all_results, f, indent=4)
            
        print(f"\\nScraping complete. Total aggregated results: {len(all_results)}")
        print("Results saved to v1_results.json")

if __name__ == "__main__":
    asyncio.run(main())
