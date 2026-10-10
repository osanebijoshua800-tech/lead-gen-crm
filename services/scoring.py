def calculate_lead_score(lead_data):
    """Calculates a lead quality score (0 - 100) based on data completeness and web presence."""
    score = 30  # Base starting score for discovered leads

    # Contact Info Completeness
    if lead_data.get("email"):
        score += 25  # High priority: Direct email contact
    if lead_data.get("phone"):
        score += 15
    if lead_data.get("website"):
        score += 15

    # Web Presence Quality Checks
    website = lead_data.get("website", "").lower()
    if "linktr.ee" in website or "wa.me" in website:
        score += 10  # Active social / business landing link

    # Category / Niche Bonus
    category = lead_data.get("category", "").lower()
    high_value_keywords = [
        "architecture",
        "construction",
        "real estate",
        "software",
        "agency",
        "consulting",
        "legal",
        "dental",
        "plumber",
    ]
    if any(keyword in category for keyword in high_value_keywords):
        score += 10

    # Ensure score stays strictly within 0 to 100 range
    return min(max(score, 0), 100)