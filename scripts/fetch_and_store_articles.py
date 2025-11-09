#!/usr/bin/env python3
"""
Function to fetch articles from TechCrunch AI category, filter by year,
and store them in SQLite database if they don't already exist.
"""

import sqlite3
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import sys
from pathlib import Path

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import functions from other scripts
from extract_links import extract_links
from filter_links import filter_links
from fetch_html_text import fetch_html_text


def setup_database(db_path='articles.db'):
    """
    Set up SQLite database with required schema.
    
    Args:
        db_path (str): Path to SQLite database file
    
    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            "Article Date" TEXT,
            "Article Header" TEXT,
            "Article Body" TEXT,
            "Fetched at" TEXT,
            "Article URL" TEXT UNIQUE
        )
    ''')
    
    conn.commit()
    return conn


def link_exists(conn, url):
    """
    Check if a link already exists in the database.
    
    Args:
        conn (sqlite3.Connection): Database connection
        url (str): Article URL to check
    
    Returns:
        bool: True if link exists, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM articles WHERE "Article URL" = ?', (url,))
    return cursor.fetchone() is not None


def save_article(conn, url, article_data):
    """
    Save article data to the database.
    
    Args:
        conn (sqlite3.Connection): Database connection
        url (str): Article URL
        article_data (dict): Dictionary with 'date', 'headline', and 'body' keys
    """
    cursor = conn.cursor()
    fetched_at = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO articles ("Article Date", "Article Header", "Article Body", "Fetched at", "Article URL")
        VALUES (?, ?, ?, ?, ?)
    ''', (
        article_data.get('date', ''),
        article_data.get('headline', ''),
        article_data.get('body', ''),
        fetched_at,
        url
    ))
    
    conn.commit()


def fetch_and_store_articles(source_url='https://techcrunch.com/category/artificial-intelligence/', 
                            filter_pattern='*/2025/*',
                            db_path='articles.db'):
    """
    Main function to fetch links, filter them, check database, and store new articles.
    
    Args:
        source_url (str): URL to extract links from
        filter_pattern (str): Glob pattern to filter links (e.g., '*/2025/*')
        db_path (str): Path to SQLite database file
    
    Returns:
        dict: Summary with 'total_links', 'filtered_links', 'new_articles', 'skipped_articles', 'errors'
    """
    # Set up database
    conn = setup_database(db_path)
    
    # Step 1: Fetch HTML from source URL
    print(f"📥 Fetching HTML from: {source_url}")
    try:
        with urlopen(source_url) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
    except (URLError, HTTPError) as e:
        print(f"❌ Error fetching source URL: {e}", file=sys.stderr)
        conn.close()
        raise
    
    # Step 2: Extract links
    print("🔗 Extracting links...")
    base_url = source_url
    all_links = extract_links(html_content, base_url)
    print(f"   Found {len(all_links)} total links")
    
    # Step 3: Filter links
    print(f"🔍 Filtering links with pattern: {filter_pattern}")
    filtered_links = filter_links(all_links, filter_pattern, use_glob=True)
    print(f"   Found {len(filtered_links)} matching links")
    
    # Step 4: Process each link
    new_articles = 0
    skipped_articles = 0
    errors = []
    
    for i, link in enumerate(filtered_links, 1):
        print(f"\n[{i}/{len(filtered_links)}] Processing: {link[:80]}...")
        
        # Check if link exists in database
        if link_exists(conn, link):
            print("   ⏭️  Already in database, skipping...")
            skipped_articles += 1
            continue
        
        # Fetch article content
        try:
            print("   📄 Fetching article content...")
            article_data = fetch_html_text(link)
            
            # Only save if we got meaningful content
            if article_data.get('headline') or article_data.get('body'):
                save_article(conn, link, article_data)
                print(f"   ✅ Saved: {article_data.get('headline', 'No headline')[:60]}...")
                new_articles += 1
            else:
                print("   ⚠️  No content extracted, skipping...")
                skipped_articles += 1
                
        except Exception as e:
            error_msg = f"Error processing {link}: {str(e)}"
            print(f"   ❌ {error_msg}")
            errors.append(error_msg)
            skipped_articles += 1
    
    conn.close()
    
    # Summary
    summary = {
        'total_links': len(all_links),
        'filtered_links': len(filtered_links),
        'new_articles': new_articles,
        'skipped_articles': skipped_articles,
        'errors': errors
    }
    
    return summary


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch articles from TechCrunch AI category and store in SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_and_store_articles.py
  python3 fetch_and_store_articles.py --db-path my_articles.db
  python3 fetch_and_store_articles.py --url https://techcrunch.com/category/ai/ --pattern '*/2024/*'
        """
    )
    parser.add_argument('--url', 
                       default='https://techcrunch.com/category/artificial-intelligence/',
                       help='Source URL to extract links from (default: TechCrunch AI category)')
    parser.add_argument('--pattern',
                       default='*/2025/*',
                       help='Glob pattern to filter links (default: */2025/*)')
    parser.add_argument('--db-path',
                       default='articles.db',
                       help='Path to SQLite database file (default: articles.db)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Starting article fetch and store process...\n")
        summary = fetch_and_store_articles(
            source_url=args.url,
            filter_pattern=args.pattern,
            db_path=args.db_path
        )
        
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"Total links found: {summary['total_links']}")
        print(f"Links matching pattern: {summary['filtered_links']}")
        print(f"New articles saved: {summary['new_articles']}")
        print(f"Articles skipped: {summary['skipped_articles']}")
        if summary['errors']:
            print(f"Errors encountered: {len(summary['errors'])}")
            for error in summary['errors']:
                print(f"  - {error}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

