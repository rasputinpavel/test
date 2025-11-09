#!/usr/bin/env python3
"""
Simple function to extract links from HTML content.
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen


def extract_links(html_content, base_url=None):
    """
    Extract all links from HTML content.
    
    Args:
        html_content (str): HTML content as string
        base_url (str, optional): Base URL for resolving relative links
    
    Returns:
        list: List of absolute URLs found in the HTML
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        if base_url:
            href = urljoin(base_url, href)
        links.append(href)
    
    return links


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 extract_links.py <html_file_or_url> [base_url]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # Check if input is a URL
    if input_path.startswith('http://') or input_path.startswith('https://'):
        with urlopen(input_path) as response:
            html = response.read().decode('utf-8')
        base = sys.argv[2] if len(sys.argv) > 2 else input_path
    else:
        # Treat as local file
        with open(input_path, 'r', encoding='utf-8') as f:
            html = f.read()
        base = sys.argv[2] if len(sys.argv) > 2 else None
    
    for link in extract_links(html, base):
        print(link)

