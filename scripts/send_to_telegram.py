#!/usr/bin/env python3
"""
Standalone script to send article notifications to Telegram channel.
Can be used independently or imported by other scripts.

Environment variables required:
- TELEGRAM_BOT_TOKEN: Your Telegram bot token
- CHANNEL_ID: Your Telegram channel ID (e.g., @channelname or -1001234567890)

Usage:
    python3 send_to_telegram.py "Article Headline" "https://example.com/article" "2025-01-15" "Article preview text..."
    
    Or use as a module:
    from send_to_telegram import send_to_telegram
    send_to_telegram("Headline", "https://example.com", "2025-01-15", "Preview...")
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Try to load .env from script directory first, then current directory
    script_dir = Path(__file__).parent
    env_file = script_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try current directory
        load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

# Try to import requests for Telegram
try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  Warning: 'requests' library not installed. Install with: pip install requests", file=sys.stderr)


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
        print("❌ Error: 'requests' library is required for Telegram functionality", file=sys.stderr)
        return False
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    # Try both uppercase and lowercase versions
    channel_id = os.getenv('CHANNEL_ID') or os.getenv('channel_id') or os.getenv('TELEGRAM_CHANNEL_ID') or os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables", file=sys.stderr)
        return False
    
    if not channel_id:
        print("❌ Error: CHANNEL_ID (or channel_id) not found in environment variables", file=sys.stderr)
        print("   💡 Tip: Make sure .env file has CHANNEL_ID or channel_id", file=sys.stderr)
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
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram API error: {str(e)}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"   Error details: {error_data}", file=sys.stderr)
            except:
                print(f"   Response: {e.response.text}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Send article notification to Telegram channel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send with headline and URL only
  python3 send_to_telegram.py "Article Title" "https://example.com/article"
  
  # Send with all fields
  python3 send_to_telegram.py "Article Title" "https://example.com/article" "2025-01-15" "Article preview text..."
  
  # Send from file (read headline from first line, URL from second line)
  python3 send_to_telegram.py --file article.txt
        """
    )
    
    parser.add_argument('headline', nargs='?', help='Article headline')
    parser.add_argument('url', nargs='?', help='Article URL')
    parser.add_argument('date', nargs='?', default='', help='Article date (optional)')
    parser.add_argument('body_preview', nargs='?', default='', help='Article body preview (optional)')
    parser.add_argument('--file', help='Read article data from file (headline on line 1, URL on line 2, date on line 3, body on line 4+)')
    
    args = parser.parse_args()
    
    # If file is provided, read from file
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                if len(lines) >= 2:
                    headline = lines[0]
                    url = lines[1]
                    date = lines[2] if len(lines) > 2 else ''
                    body_preview = '\n'.join(lines[3:]) if len(lines) > 3 else ''
                else:
                    print("❌ Error: File must contain at least headline (line 1) and URL (line 2)", file=sys.stderr)
                    sys.exit(1)
        except FileNotFoundError:
            print(f"❌ Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use command line arguments
        if not args.headline or not args.url:
            parser.print_help()
            sys.exit(1)
        headline = args.headline
        url = args.url
        date = args.date
        body_preview = args.body_preview
    
    # Send to Telegram
    print(f"📤 Sending to Telegram channel...")
    print(f"   Headline: {headline[:60]}...")
    print(f"   URL: {url}")
    
    if send_to_telegram(headline, url, date, body_preview):
        print("✅ Successfully sent to Telegram channel!")
        sys.exit(0)
    else:
        print("❌ Failed to send to Telegram channel", file=sys.stderr)
        sys.exit(1)

