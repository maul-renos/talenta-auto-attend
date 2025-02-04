import os
import asyncio
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import calendar
from utils.holidays import PUBLIC_HOLIDAYS

load_dotenv()

async def main():
    is_headless = os.getenv("HEADLESS_BROWSER", "true") == "true"
    now = datetime.now(timezone.utc).astimezone()
    today = now.strftime("%-d %b %Y")
    latitude = os.getenv("GEO_LATITUDE")
    longitude = os.getenv("GEO_LONGITUDE")
    
    if now.weekday() == 4:  # Friday
        latitude = os.getenv("ONSITE_GEO_LATITUDE")
        longitude = os.getenv("ONSITE_GEO_LONGITUDE")

    if today in PUBLIC_HOLIDAYS:
        print("Today is a public holiday, skipping check-in/out...")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=is_headless)
        context = await browser.new_context(
            viewport={"width": 1080, "height": 560},
            geolocation={"latitude": float(latitude), "longitude": float(longitude)},
            permissions=["geolocation"]
        )
        page = await context.new_page()
        
        print("Opening login page...")
        await page.goto("https://account.mekari.com/users/sign_in?client_id=TAL-73645")
        
        print("Filling in account email & password...")
        await page.fill("#user_email", os.getenv("ACCOUNT_EMAIL"))
        await page.fill("#user_password", os.getenv("ACCOUNT_PASSWORD"))
        
        print("Signing in...")
        await page.click("#new-signin-button")
        await page.wait_for_load_state("networkidle")
        
        dashboard = await page.locator("text=Dashboard").count()
        if dashboard > 0:
            print("Successfully logged in...")
        else:
            print("Failed to log in...")
            await browser.close()
            return
        
        my_name = (await page.locator("#navbar-name").text_content()).strip()
        who_is_off_today = await page.locator(".tl-card-small", has_text="Who's Off").inner_text()
        
        if my_name in who_is_off_today:
            print("You are off today, skipping check-in/out...")
            await browser.close()
            return
        
        print("Navigating to 'My Attendance Logs'...")
        await page.click("text=My Attendance Logs")
        await page.wait_for_selector("h3:text('Present')")
        
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        if now.day > 18 and now.day <= days_in_month:
            next_month = (now + timedelta(days=30)).strftime("%b %Y")
            print(f"Today is after the 18th, switching to the next month: {next_month}")
            date_input = page.locator('#datepicker-attendance-detail-input')
            await date_input.fill(next_month)
            await date_input.press("Enter")
        
        row_today = page.locator(f"tr:has-text('{today}')").first
        column_check_day_off = (await row_today.locator("td:nth-child(2)").text_content()).strip()
        column_check_on_leave = (await row_today.locator("td:nth-child(7)").text_content()).strip()
        column_check_check_in_time = (await row_today.locator("td:nth-child(5)").text_content()).strip()
        column_check_check_out_time = (await row_today.locator("td:nth-child(6)").text_content()).strip()
        
        if column_check_day_off != "N" or column_check_on_leave == "CT":
            print("Skipping check-in/out due to holiday or leave...")
            await browser.close()
            return
        
        if column_check_check_in_time != "-" and os.getenv("CHECK_TYPE") == "CHECK_IN":
            print("Already checked in, skipping...")
            await browser.close()
            return
        
        if column_check_check_out_time != "-" and os.getenv("CHECK_TYPE") == "CHECK_OUT":
            print("Already checked out, skipping...")
            await browser.close()
            return
        
        await browser.close()
