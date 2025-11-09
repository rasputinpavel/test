#!/usr/bin/env python3
"""
Batch fetch articles from a list of URLs in a file.
Uses fetch_html_text to download and extract text from multiple URLs.
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from fetch_html_text import fetch_html_text


def parse_date(date_str):
    """
    Parse date string and return datetime object.
    Handles formats like "12:53 PM PST · November 8, 2025"
    """
    if not date_str:
        return None
    
    # Try to extract date part (after the · or •)
    date_match = re.search(r'[·•]\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})', date_str)
    if date_match:
        date_part = date_match.group(1)
    else:
        # Try other patterns
        date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4})', date_str)
        if date_match:
            date_part = date_match.group(1)
        else:
            # Try YYYY-MM-DD format
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                try:
                    return datetime.strptime(date_match.group(1), '%Y-%m-%d')
                except:
                    pass
            return None
    
    # Parse the date
    try:
        return datetime.strptime(date_part, '%B %d, %Y')
    except:
        try:
            return datetime.strptime(date_part, '%b %d, %Y')
        except:
            return None


def format_filename(date, headline_slug):
    """
    Create filename with date prefix: YYYY-MM-DD_headline-slug.txt
    """
    if date:
        date_str = date.strftime('%Y-%m-%d')
        return f"{date_str}_{headline_slug}.txt"
    else:
        return f"{headline_slug}.txt"


def fetch_articles_from_file(urls_file, output_dir=None, verbose=True):
    """
    Fetch articles from URLs listed in a file.
    
    Args:
        urls_file (str): Path to file containing URLs (one per line)
        output_dir (str, optional): Directory to save articles. If None, uses 'articles' directory
        verbose (bool): Print progress messages
    
    Returns:
        dict: Summary with success count, failure count, and file paths
    """
    urls_path = Path(urls_file)
    if not urls_path.exists():
        raise FileNotFoundError(f"URLs file not found: {urls_file}")
    
    # Set up output directory
    if output_dir is None:
        output_dir = Path.cwd() / "articles"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    # Read URLs from file
    with open(urls_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    if verbose:
        print(f"📋 Found {len(urls)} URLs to fetch")
        print(f"📁 Saving articles to: {output_dir}")
        print()
    
    results = {
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    # Store articles with their dates for sorting
    articles_data = []
    
    # Fetch each URL
    for i, url in enumerate(urls, 1):
        if verbose:
            print(f"[{i}/{len(urls)}] Fetching: {url[:60]}...")
        
        try:
            # Fetch article content
            result = fetch_html_text(url)
            
            # Parse date
            article_date = parse_date(result['date'])
            
            # Generate headline slug for filename
            headline_slug = result['headline'].lower() if result['headline'] else 'article'
            # Clean slug: keep only alphanumeric, spaces, and hyphens, then replace spaces with hyphens
            headline_slug = re.sub(r'[^a-z0-9\s-]', '', headline_slug)
            headline_slug = re.sub(r'\s+', '-', headline_slug).strip('-')
            headline_slug = headline_slug[:80]  # Limit length
            if not headline_slug:
                # Fallback to URL slug
                url_parts = url.rstrip('/').split('/')
                headline_slug = url_parts[-1] if url_parts[-1] else url_parts[-2]
                headline_slug = "".join(c for c in headline_slug if c.isalnum() or c in ('-', '_'))[:80]
                if not headline_slug:
                    headline_slug = f"article_{i}"
            
            # Create filename with date
            filename = format_filename(article_date, headline_slug)
            output_path = output_dir / filename
            
            # Format output with Date, Headline, and Text Body
            output = f"Date: {result['date']}\n\n"
            output += f"Headline: {result['headline']}\n\n"
            output += f"Text Body:\n{result['body']}\n"
            
            # Save article
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            # Store for sorting
            articles_data.append({
                'path': output_path,
                'date': article_date,
                'filename': filename
            })
            
            results['success'] += 1
            results['files'].append(str(output_path))
            
            if verbose:
                body_len = len(result['body'])
                headline_preview = result['headline'][:40] + "..." if len(result['headline']) > 40 else result['headline']
                print(f"   ✅ Saved: {filename}")
                print(f"      📅 {result['date']}")
                print(f"      📰 {headline_preview}")
                print(f"      📊 {body_len} chars")
        
        except Exception as e:
            results['failed'] += 1
            if verbose:
                print(f"   ❌ Failed: {str(e)}")
        
        if verbose:
            print()
    
    # Sort articles by date (descending - newest first)
    # Articles without dates go to the end
    articles_data.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)
    
    if verbose and articles_data:
        print("=" * 60)
        print("📅 Articles sorted by date (newest first):")
        print("=" * 60)
        for i, article in enumerate(articles_data[:10], 1):  # Show first 10
            date_str = article['date'].strftime('%Y-%m-%d') if article['date'] else 'No date'
            print(f"   {i}. {date_str} - {article['filename']}")
        if len(articles_data) > 10:
            print(f"   ... and {len(articles_data) - 10} more")
        print()
    
    # Print summary
    if verbose:
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   ✅ Success: {results['success']}")
        print(f"   ❌ Failed: {results['failed']}")
        print(f"   📁 Output directory: {output_dir}")
        print("=" * 60)
    
    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_articles_batch.py <urls_file> [output_dir]")
        print("\nExamples:")
        print("  python3 fetch_articles_batch.py filtered_links.txt")
        print("  python3 fetch_articles_batch.py filtered_links.txt articles/")
        sys.exit(1)
    
    urls_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        fetch_articles_from_file(urls_file, output_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

