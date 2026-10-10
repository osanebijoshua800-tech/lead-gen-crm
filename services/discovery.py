import os
import re
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from utils.cleaner import clean_business_name, normalize_phone, normalize_url


def scrape_email_from_website(url):
    """
    Attempts to fetch the homepage and extract a business contact email address.
    """
    if not url:
        return ""

    normalized_url = normalize_url(url)
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(normalized_url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Search page text for email patterns
            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', soup.get_text()
            )

            # Filter out common image extensions or fake emails captured by regex
            valid_emails = [
                e
                for e in emails
                if not e.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
                )
            ]
            if valid_emails:
                return valid_emails[0]
    except Exception:
        pass

    return ""


def search_google_businesses(niche, location, limit=5):
    """
    Queries Google Maps via SerpAPI, cleans lead data, and scrapes emails from websites.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("Warning: SERPAPI_KEY is missing from .env file.")
        return []

    params = {
        "engine": "google_maps",
        "q": f"{niche} in {location}",
        "api_key": api_key,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        local_results = results.get("local_results", [])

        businesses = []
        for item in local_results[:limit]:
            raw_name = item.get("title", "")
            raw_phone = item.get("phone", "")
            raw_website = item.get("website", "")

            # Scrape email from the business website if available
            extracted_email = scrape_email_from_website(raw_website)

            businesses.append(
                {
                    "business_name": clean_business_name(raw_name),
                    "category": item.get("type", niche).strip().title(),
                    "location": item.get("address", location).strip(),
                    "website": normalize_url(raw_website),
                    "phone": normalize_phone(raw_phone),
                    "email": extracted_email,
                }
            )
        return businesses
    except Exception as e:
        print(f"Error querying SerpAPI: {e}")
        return []