import re

def clean_business_name(name):
    """
    Normalizes business names by stripping trailing whitespace, corporate suffixes, 
    and extra punctuation to improve match consistency.
    """
    if not name:
        return ""
    
    cleaned = name.strip()
    # Remove common corporate suffixes for deduplication comparison
    cleaned = re.sub(r'(?i)\b(inc|llc|co|corp|corporation|ltd|limited)\b\.?', '', cleaned)
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_phone(phone):
    """
    Cleans phone numbers into a standard readable format: +1 (XXX) XXX-XXXX or numbers only.
    """
    if not phone:
        return ""
    
    # Extract only digits and leading plus sign
    digits = re.sub(r'[^\d+]', '', phone)
    
    # Standard 10-digit US format
    if len(digits) == 10:
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return digits


def normalize_url(url):
    """
    Ensures website URLs have a valid http:// or https:// scheme and removes trailing slashes.
    """
    if not url:
        return ""
    
    cleaned_url = url.strip().lower()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = "https://" + cleaned_url
        
    return cleaned_url.rstrip("/")