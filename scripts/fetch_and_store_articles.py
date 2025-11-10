#!/usr/bin/env python3
"""
Function to fetch articles from TechCrunch AI category, filter by year,
and store them in SQLite database if they don't already exist.
New articles are automatically sent to a Telegram channel if configured.

Publication Status:
- New articles are saved with "Unpublished" status
- Only "Unpublished" articles are sent to Telegram
- After successful Telegram send, articles are marked as "Published"
- Existing articles older than 1 day are automatically marked as "Published"
- Articles from today to 1 day ago are marked as "Unpublished"

Environment variables required for Telegram:
- TELEGRAM_BOT_TOKEN: Your Telegram bot token
- CHANNEL_ID: Your Telegram channel ID (e.g., @channelname or -1001234567890)
"""

import sqlite3
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import sys
import os
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import functions from other scripts
from extract_links import extract_links
from filter_links import filter_links
from fetch_html_text import fetch_html_text

# Try to import requests for Telegram
try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


def setup_database(db_path='articles.db'):
    """
    Set up SQLite database with required schema.
    Adds "Published at" column if it doesn't exist and migrates existing articles.
    
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
            "Article URL" TEXT UNIQUE,
            "Published at" TEXT DEFAULT "Unpublished"
        )
    ''')
    
    # Check if "Published at" column exists, if not add it
    cursor.execute("PRAGMA table_info(articles)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "Published at" not in columns:
        print("📝 Adding 'Published at' column to database...")
        try:
            # Add column with DEFAULT value
            cursor.execute('ALTER TABLE articles ADD COLUMN "Published at" TEXT DEFAULT "Unpublished"')
            conn.commit()
            print("   ✅ Column added successfully")
            
            # Migrate existing articles based on their age
            migrate_publication_status(conn)
        except sqlite3.OperationalError as e:
            print(f"   ⚠️  Error adding column: {e}")
            # Try without DEFAULT (SQLite version might not support it in ALTER TABLE)
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN "Published at" TEXT')
                conn.commit()
                # Set default for all existing rows
                cursor.execute('UPDATE articles SET "Published at" = "Unpublished" WHERE "Published at" IS NULL')
                conn.commit()
                print("   ✅ Column added (without DEFAULT)")
                migrate_publication_status(conn)
            except sqlite3.OperationalError as e2:
                print(f"   ❌ Failed to add column: {e2}")
                raise
    
    conn.commit()
    return conn


def migrate_publication_status(conn):
    """
    Migrate existing articles to set publication status:
    - Articles older than 1 day: "Published"
    - Articles from today to 1 day ago: "Unpublished"
    
    Args:
        conn (sqlite3.Connection): Database connection
    """
    cursor = conn.cursor()
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    
    # Get all articles to check and update their status based on age
    cursor.execute('SELECT ID, "Fetched at", "Published at" FROM articles')
    articles = cursor.fetchall()
    
    if not articles:
        print("   No articles to migrate")
        return
    
    published_count = 0
    unpublished_count = 0
    skipped_count = 0
    
    for article_id, fetched_at_str, current_status in articles:
        # Skip articles that are already Published (they stay Published)
        if current_status == "Published":
            skipped_count += 1
            continue
        
        if not fetched_at_str:
            # If no "Fetched at" date, set to Unpublished
            cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ("Unpublished", article_id))
            unpublished_count += 1
            continue
        
        try:
            # Parse the ISO format date
            fetched_at = datetime.fromisoformat(fetched_at_str)
            
            # If article is older than 1 day, mark as Published
            if fetched_at < one_day_ago:
                cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ("Published", article_id))
                published_count += 1
            else:
                # Articles from today to 1 day ago are Unpublished
                cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ("Unpublished", article_id))
                unpublished_count += 1
        except (ValueError, TypeError) as e:
            # If date parsing fails, set to Unpublished
            print(f"   ⚠️  Warning: Could not parse date for article ID {article_id}: {e}")
            cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ("Unpublished", article_id))
            unpublished_count += 1
    
    conn.commit()
    print(f"   ✅ Migrated {len(articles)} articles:")
    print(f"      📤 Published (older than 1 day): {published_count}")
    print(f"      📝 Unpublished (within 1 day): {unpublished_count}")
    if skipped_count > 0:
        print(f"      ⏭️  Skipped (already Published): {skipped_count}")


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


def send_to_telegram(headline, url, date='', body_preview=''):
    """
    Send article notification to Telegram channel.
    
    Args:
        headline (str): Article headline
        url (str): Article URL
        date (str): Article date (optional)
        body_preview (str): Preview of article body (optional, truncated)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not TELEGRAM_AVAILABLE:
        return False
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    channel_id = os.getenv('CHANNEL_ID')
    
    if not bot_token or not channel_id:
        return False
    
    # Format message
    message_parts = []
    
    if headline:
        message_parts.append(f"📰 *{headline}*")
    
    if date:
        message_parts.append(f"📅 {date}")
    
    if body_preview:
        # Truncate body preview to fit Telegram message limit (4096 chars)
        # Reserve space for headline, date, URL, and formatting
        max_body_length = 3000
        if len(body_preview) > max_body_length:
            body_preview = body_preview[:max_body_length] + "..."
        message_parts.append(f"\n{body_preview}")
    
    message_parts.append(f"\n🔗 {url}")
    
    message = "\n".join(message_parts)
    
    # Telegram has a 4096 character limit per message
    if len(message) > 4096:
        # Truncate message, keeping headline, date, and URL
        max_length = 4096 - len(url) - 50  # Reserve space for URL and formatting
        if body_preview:
            # Recalculate body preview to fit
            available_space = max_length - len(headline) - len(date) - 100  # Reserve for formatting
            if available_space > 0:
                body_preview = body_preview[:available_space] + "..."
                message_parts = [
                    f"📰 *{headline}*" if headline else "",
                    f"📅 {date}" if date else "",
                    f"\n{body_preview}" if body_preview else "",
                    f"\n🔗 {url}"
                ]
                message = "\n".join([p for p in message_parts if p])
            else:
                # If still too long, just send headline, date, and URL
                message_parts = [
                    f"📰 *{headline}*" if headline else "",
                    f"📅 {date}" if date else "",
                    f"\n🔗 {url}"
                ]
                message = "\n".join([p for p in message_parts if p])
    
    # Telegram API endpoint
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        payload = {
            'chat_id': channel_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"   ⚠️  Telegram error: {str(e)}", file=sys.stderr)
        return False


def save_article(conn, url, article_data):
    """
    Save article data to the database.
    New articles are set to "Unpublished" status.
    
    Args:
        conn (sqlite3.Connection): Database connection
        url (str): Article URL
        article_data (dict): Dictionary with 'date', 'headline', and 'body' keys
    
    Returns:
        int: Article ID
    """
    cursor = conn.cursor()
    fetched_at = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO articles ("Article Date", "Article Header", "Article Body", "Fetched at", "Article URL", "Published at")
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        article_data.get('date', ''),
        article_data.get('headline', ''),
        article_data.get('body', ''),
        fetched_at,
        url,
        "Unpublished"  # New articles start as Unpublished
    ))
    
    conn.commit()
    return cursor.lastrowid


def mark_as_published(conn, url):
    """
    Mark an article as Published after successful Telegram send.
    
    Args:
        conn (sqlite3.Connection): Database connection
        url (str): Article URL
    """
    cursor = conn.cursor()
    cursor.execute('UPDATE articles SET "Published at" = ? WHERE "Article URL" = ?', ("Published", url))
    conn.commit()


def is_unpublished(conn, url):
    """
    Check if an article is unpublished.
    
    Args:
        conn (sqlite3.Connection): Database connection
        url (str): Article URL
    
    Returns:
        bool: True if article is unpublished, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute('SELECT "Published at" FROM articles WHERE "Article URL" = ?', (url,))
    result = cursor.fetchone()
    
    if result is None:
        return False  # Article doesn't exist
    
    published_at = result[0]
    return published_at == "Unpublished" or published_at is None


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
    telegram_sent = 0
    telegram_failed = 0
    errors = []
    
    for i, link in enumerate(filtered_links, 1):
        print(f"\n[{i}/{len(filtered_links)}] Processing: {link[:80]}...")
        
        # Check if link exists in database
        if link_exists(conn, link):
            # Check if it's unpublished and should be sent to Telegram
            if is_unpublished(conn, link):
                print("   📝 Article exists but is unpublished, checking if should send to Telegram...")
                # Get article data from database
                cursor = conn.cursor()
                cursor.execute('SELECT "Article Header", "Article Date", "Article Body" FROM articles WHERE "Article URL" = ?', (link,))
                result = cursor.fetchone()
                
                if result:
                    headline = result[0] or ''
                    date = result[1] or ''
                    body = result[2] or ''
                    body_preview = body[:500] if body else ''
                    
                    # Send to Telegram channel (only unpublished articles)
                    if send_to_telegram(headline, link, date, body_preview):
                        print("   📤 Sent to Telegram channel")
                        mark_as_published(conn, link)
                        print("   ✅ Marked as Published")
                        telegram_sent += 1
                    else:
                        print("   ⚠️  Could not send to Telegram (check TELEGRAM_BOT_TOKEN and CHANNEL_ID)")
                        telegram_failed += 1
                else:
                    print("   ⏭️  Could not retrieve article data, skipping...")
            else:
                print("   ⏭️  Already in database and published, skipping...")
            skipped_articles += 1
            continue
        
        # Fetch article content for new articles
        try:
            print("   📄 Fetching article content...")
            article_data = fetch_html_text(link)
            
            # Only save if we got meaningful content
            if article_data.get('headline') or article_data.get('body'):
                save_article(conn, link, article_data)
                print(f"   ✅ Saved (Unpublished): {article_data.get('headline', 'No headline')[:60]}...")
                
                # Send to Telegram channel (new articles are automatically Unpublished)
                headline = article_data.get('headline', '')
                date = article_data.get('date', '')
                body = article_data.get('body', '')
                # Truncate body for preview (first 500 chars)
                body_preview = body[:500] if body else ''
                
                # Send to Telegram channel
                if send_to_telegram(headline, link, date, body_preview):
                    print("   📤 Sent to Telegram channel")
                    mark_as_published(conn, link)
                    print("   ✅ Marked as Published")
                    telegram_sent += 1
                else:
                    print("   ⚠️  Could not send to Telegram (check TELEGRAM_BOT_TOKEN and CHANNEL_ID)")
                    telegram_failed += 1
                
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
        'telegram_sent': telegram_sent,
        'telegram_failed': telegram_failed,
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
        if summary.get('telegram_sent', 0) > 0 or summary.get('telegram_failed', 0) > 0:
            print(f"Telegram notifications sent: {summary.get('telegram_sent', 0)}")
            if summary.get('telegram_failed', 0) > 0:
                print(f"Telegram notifications failed: {summary.get('telegram_failed', 0)}")
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

