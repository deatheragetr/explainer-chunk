import re

def make_url_friendly(filename: str) -> str:
    # Remove any non-alphanumeric characters except for periods and hyphens
    filename = re.sub(r'[^\w\-\.]', '', filename)
    # Replace spaces with hyphens
    filename = filename.replace(' ', '-')
    # Convert to lowercase
    filename = filename.lower()
    # Truncate if too long (e.g., limit to 100 characters)
    filename = filename[:100]
    return filename
