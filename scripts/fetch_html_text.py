#!/usr/bin/env python3
"""
Function to fetch HTML page text by downloading from URL or reading from file.
Extracts and returns structured content: Date, Headline, and Text Body.
"""

from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path
import re


def fetch_html_text(source):
    """
    Fetch HTML page text from a URL or local file.
    Extracts structured content: Date, Headline, and Text Body.
    
    Args:
        source (str): URL (http:// or https://) or path to local HTML file
    
    Returns:
        dict: Dictionary with 'date', 'headline', and 'body' keys
    
    Raises:
        FileNotFoundError: If local file doesn't exist
        URLError: If URL cannot be accessed
        HTTPError: If HTTP request fails
        ValueError: If source is neither a valid URL nor a file path
    """
    # Check if source is a URL
    if source.startswith('http://') or source.startswith('https://'):
        try:
            with urlopen(source) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
        except HTTPError as e:
            raise HTTPError(e.url, e.code, f"HTTP Error {e.code}: {e.reason}", e.headers, e.fp)
        except URLError as e:
            raise URLError(f"Failed to fetch URL: {e.reason}")
    else:
        # Treat as local file path
        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {source}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
        except Exception as e:
            raise IOError(f"Error reading file {source}: {str(e)}")
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, nav, footer, and other non-content elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()
    
    # Extract headline
    headline = ""
    # Try common headline selectors
    for selector in ['h1', 'article h1', '.article-title', '.post-title', 'title']:
        element = soup.select_one(selector)
        if element:
            headline = element.get_text(strip=True)
            # Remove site name if present (e.g., "Title | TechCrunch")
            if '|' in headline:
                headline = headline.split('|')[0].strip()
            if headline:
                break
    
    # Extract date
    date = ""
    # Look for time elements
    time_elem = soup.find('time')
    if time_elem:
        date = time_elem.get_text(strip=True)
        if not date and time_elem.get('datetime'):
            date = time_elem.get('datetime')
    
    # If no time element, look for date patterns in text
    if not date:
        # Common date patterns
        date_patterns = [
            r'\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:PST|EST|CST|MST|UTC)?\s*[·•]\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}',  # "12:22 PM PST · November 6, 2025"
            r'[A-Z][a-z]+\s+\d{1,2},\s+\d{4}',  # "November 6, 2025"
            r'\d{1,2}/\d{1,2}/\d{4}',  # "11/06/2025"
            r'\d{4}-\d{2}-\d{2}',  # "2025-11-06"
        ]
        
        text_content = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text_content)
            if match:
                date = match.group(0)
                break
    
    # Extract article body
    body = ""
    
    # Try to find main article content
    article = soup.find('article')
    if article:
        # Remove unwanted elements from article
        for elem in article.find_all(['nav', 'footer', 'aside', 'header', 'script', 'style', 'time']):
            elem.decompose()
        # Extract paragraphs to preserve structure
        paragraphs = article.find_all('p')
        if paragraphs:
            body_parts = []
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if len(text) > 50:
                    body_parts.append(text)
            if body_parts:
                body = '\n\n'.join(body_parts)
        else:
            body = article.get_text(separator=' ', strip=True)
    else:
        # Try common content selectors
        for selector in ['.article-content', '.post-content', '.entry-content', 'main', '.content']:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove unwanted elements
                for elem in content_elem.find_all(['nav', 'footer', 'aside', 'header', 'script', 'style', 'time']):
                    elem.decompose()
                # Try to extract paragraphs first
                paragraphs = content_elem.find_all('p')
                if paragraphs:
                    body_parts = []
                    for p in paragraphs:
                        text = p.get_text(separator=' ', strip=True)
                        if len(text) > 50:
                            body_parts.append(text)
                    if body_parts:
                        body = '\n\n'.join(body_parts)
                        if len(body) > 200:
                            break
                else:
                    body = content_elem.get_text(separator=' ', strip=True)
                    if body and len(body) > 200:
                        break
    
    # If still no body, try to extract from main content area
    if not body or len(body) < 200:
        # Remove all navigation and footer elements
        for elem in soup.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
            elem.decompose()
        
        # Get all paragraphs - prefer this method as it preserves paragraph structure
        paragraphs = soup.find_all('p')
        if paragraphs:
            body_parts = []
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)  # Use space separator to keep sentences together
                # Filter out short paragraphs that are likely navigation/meta
                if len(text) > 50 and not any(skip in text.lower() for skip in ['subscribe', 'newsletter', 'register', 'cookie', 'privacy policy', 'view bio', 'you can contact']):
                    body_parts.append(text)
            if body_parts:
                body = '\n\n'.join(body_parts)
    
    # Clean up body text
    if body:
        # Split into paragraphs (already separated by \n\n)
        paragraphs = body.split('\n\n')
        
        # Filter out paragraphs that are navigation/footer content
        filtered_paragraphs = []
        skip_keywords = ['subscribe', 'newsletter', 'register', 'cookie', 'privacy', 'terms', 'contact us', 'advertise', 
                        'view bio', 'you can contact', 'topics', 'related', 'latest in', 'image credits', 'posted:', 
                        'in brief', 'techcrunch', '©']
        
        for para in paragraphs:
            para = para.strip()
            # Keep paragraphs that are substantial and don't contain skip keywords
            if len(para) > 50 and not any(keyword in para.lower() for keyword in skip_keywords):
                filtered_paragraphs.append(para)
        
        body = '\n\n'.join(filtered_paragraphs)
    
    return {
        'date': date.strip() if date else '',
        'headline': headline.strip() if headline else '',
        'body': body.strip() if body else ''
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_html_text.py <url_or_file> [output_file]")
        print("\nExamples:")
        print("  python3 fetch_html_text.py https://example.com")
        print("  python3 fetch_html_text.py page.html")
        print("  python3 fetch_html_text.py https://example.com output.txt")
        sys.exit(1)
    
    source = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = fetch_html_text(source)
        
        # Format output
        output = f"Date: {result['date']}\n\n"
        output += f"Headline: {result['headline']}\n\n"
        output += f"Text Body:\n{result['body']}\n"
        
        if output_file:
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✅ Article saved to: {output_file}")
            print(f"📅 Date: {result['date']}")
            print(f"📰 Headline: {result['headline'][:60]}..." if len(result['headline']) > 60 else f"📰 Headline: {result['headline']}")
            print(f"📊 Body length: {len(result['body'])} characters")
        else:
            # Print to stdout
            print(output)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (URLError, HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

