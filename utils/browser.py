from playwright.async_api import async_playwright

async def setup_browser(latitude, longitude, headless=True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 560},
            geolocation={"latitude": float(latitude), "longitude": float(longitude)},
            permissions=["geolocation"]
        )
        return browser, context
