import asyncio
import csv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def scrape_nobroker(location="Indiranagar, Bangalore", radius=5):
    """
    Scrapes property listings from NoBroker for a given location.
    Version 1 MVP: Extracts Location, Rent, Basic Info, and Contact status.
    """
    print(f"Starting scraper for {location} (within ~{radius}km)...")
    
    # 1. Formatting the URL
    search_query = location.split(',')[0].strip().lower().replace(' ', '-')
    city = location.split(',')[-1].strip().lower().replace(' ', '-') if ',' in location else 'bangalore'
    url = f"https://www.nobroker.in/property/rent/{city}/{search_query}"
    
    print(f"Target URL: {url}")
    
    async with async_playwright() as p:
        # 2. Launching the browser
        # We use headless=True to run it silently in the background.
        browser = await p.chromium.launch(headless=True)
        
        # 3. Setting up the browser context
        # We spoof the User-Agent to make our bot look like a real Mac Chrome browser.
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # 4. Applying Stealth Mode
        # playwright-stealth removes common bot indicators (like navigator.webdriver = true)
        # to prevent NoBroker from immediately blocking us.
        await Stealth().apply_stealth_async(page)
        
        try:
            # 5. Navigating to the page
            print("Navigating to the website...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 6. Waiting for content to load
            # Real estate sites load listings asynchronously via JS. 
            # We wait for the 'article' HTML tag, which typically wraps property cards.
            print("Waiting for property listings to render...")
            await page.wait_for_selector('article', timeout=15000)
            
            # 7. Extracting all property cards
            listings = await page.locator('article').all()
            print(f"Found {len(listings)} listings on the page.")
            
            results = []
            
            # 8. Parsing each listing
            for index, listing in enumerate(listings[:10]): # Limit to top 10 for V1
                try:
                    # Extract the Title (usually an h2 tag)
                    title_element = listing.locator('h2')
                    title = await title_element.text_content() if await title_element.count() > 0 else "N/A"
                    
                    # Extract Rent by looking for the rupee symbol
                    rent_element = listing.locator('text=₹')
                    rent = await rent_element.first.text_content() if await rent_element.count() > 0 else "N/A"
                    
                    # Extract Size (sqft)
                    size_element = listing.locator('text=sqft')
                    size = await size_element.first.text_content() if await size_element.count() > 0 else "N/A"
                    
                    # Extract Sub-location
                    location_detail = await title_element.evaluate("el => el.nextElementSibling ? el.nextElementSibling.innerText : ''") if await title_element.count() > 0 else "N/A"

                    # Determine Lister Type
                    owner_badge = listing.locator('text=Owner')
                    listed_by = "Owner" if await owner_badge.count() > 0 else "Broker/Other"
                    
                    # 9. Structure the extracted data
                    property_data = {
                        "Title": title.strip() if title else "N/A",
                        "Location_Detail": location_detail.strip() if location_detail else "N/A",
                        "Rent": rent.strip() if rent else "N/A",
                        "Size": size.strip() if size else "N/A",
                        "Listed_By": listed_by
                    }
                    
                    results.append(property_data)
                    print(f"Extracted [{index+1}]: {property_data['Title']} | {property_data['Rent']}")
                    
                except Exception as e:
                    print(f"Error extracting listing {index}: {e}")
                    
            # 10. Saving to Database/File (CSV for V1)
            if results:
                csv_filename = "nobroker_results.csv"
                keys = results[0].keys()
                with open(csv_filename, 'w', newline='', encoding='utf-8') as output_file:
                    dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(results)
                print(f"\nSuccessfully saved {len(results)} listings to {csv_filename}")
            else:
                print("No listings extracted.")
                
        except Exception as e:
            print(f"Scraping failed: {e}")
            print("Note: NoBroker has strong anti-bot mechanisms. If it timed out, they might have detected the automated browser.")
            try:
                html = await page.content()
                with open('debug.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                await page.screenshot(path="debug_error.png")
                print("Saved screenshot to debug_error.png and HTML to debug.html")
            except:
                pass
            
        finally:
            # 11. Clean up resources
            await browser.close()

if __name__ == "__main__":
    # Start the asyncio event loop
    asyncio.run(scrape_nobroker(location="Indiranagar, Bangalore", radius=5))
