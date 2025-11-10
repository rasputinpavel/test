#!/usr/bin/env python3
"""
Daily news scheduler - runs fetch_and_store_articles every day at 7:00 AM Bangkok time.
Sends new articles to Telegram channel automatically.

Usage:
    # Run once (for testing)
    python3 scripts/daily_news_scheduler.py --once
    
    # Run as daemon (keeps running and schedules daily)
    python3 scripts/daily_news_scheduler.py
    
    # Run with custom time
    python3 scripts/daily_news_scheduler.py --time "08:00"
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("⚠️  Warning: 'schedule' library not installed. Install with: pip install schedule", file=sys.stderr)

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    try:
        from zoneinfo import ZoneInfo
        PYTZ_AVAILABLE = False
        ZONEINFO_AVAILABLE = True
    except ImportError:
        PYTZ_AVAILABLE = False
        ZONEINFO_AVAILABLE = False
        print("⚠️  Warning: Timezone library not found. Install with: pip install pytz", file=sys.stderr)

from fetch_and_store_articles import fetch_and_store_articles


def get_bangkok_timezone():
    """Get Bangkok timezone object."""
    if PYTZ_AVAILABLE:
        return pytz.timezone('Asia/Bangkok')
    elif ZONEINFO_AVAILABLE:
        return ZoneInfo('Asia/Bangkok')
    else:
        # Fallback: assume UTC+7 (not ideal, but works)
        print("⚠️  Warning: Using UTC+7 offset without DST support. Install pytz for proper timezone handling.", file=sys.stderr)
        return None


def get_current_bangkok_time():
    """Get current time in Bangkok timezone."""
    bangkok_tz = get_bangkok_timezone()
    if bangkok_tz:
        if PYTZ_AVAILABLE:
            return datetime.now(bangkok_tz)
        else:
            from datetime import timezone, timedelta
            bangkok_offset = timezone(timedelta(hours=7))
            return datetime.now(bangkok_offset)
    else:
        # Fallback to local time
        return datetime.now()


def run_news_fetch(db_path='articles.db'):
    """Run the news fetch and send process."""
    bangkok_time = get_current_bangkok_time()
    print(f"\n{'='*60}")
    print(f"🕐 Scheduled run at {bangkok_time.strftime('%Y-%m-%d %H:%M:%S')} (Bangkok time)")
    print(f"{'='*60}\n")
    
    try:
        # Run the fetch and store process
        # This will automatically:
        # 1. Fetch new articles
        # 2. Store them in database (as Unpublished)
        # 3. Send unpublished articles to Telegram
        # 4. Mark sent articles as Published
        summary = fetch_and_store_articles(db_path=db_path)
        
        print(f"\n{'='*60}")
        print(f"✅ Scheduled run completed at {bangkok_time.strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"📊 Summary:")
        print(f"   New articles: {summary.get('new_articles', 0)}")
        print(f"   Telegram sent: {summary.get('telegram_sent', 0)}")
        print(f"   Telegram failed: {summary.get('telegram_failed', 0)}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error during scheduled run: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def schedule_daily_run(time_str="07:00", db_path='articles.db'):
    """Schedule daily run at specified time (Bangkok time)."""
    if not SCHEDULE_AVAILABLE:
        print("❌ Error: 'schedule' library is required. Install with: pip install schedule", file=sys.stderr)
        return False
    
    bangkok_tz = get_bangkok_timezone()
    
    # Convert Bangkok time to local time for scheduling
    # schedule library uses local system time, so we need to convert
    now_bangkok = get_current_bangkok_time()
    now_local = datetime.now()
    
    # Calculate time difference
    if PYTZ_AVAILABLE or ZONEINFO_AVAILABLE:
        # Get UTC times to calculate offset
        if PYTZ_AVAILABLE:
            utc_now = datetime.now(pytz.UTC)
            bangkok_now = utc_now.astimezone(bangkok_tz)
            offset_hours = (bangkok_now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)).total_seconds() / 3600
        else:
            from datetime import timezone
            utc_now = datetime.now(timezone.utc)
            bangkok_now = utc_now.astimezone(bangkok_tz)
            offset_hours = (bangkok_now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)).total_seconds() / 3600
    else:
        # Fallback: assume UTC+7
        offset_hours = 7
    
    # Convert Bangkok time to local time
    hour, minute = map(int, time_str.split(':'))
    bangkok_target = now_bangkok.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if bangkok_target <= now_bangkok:
        # If time already passed today, schedule for tomorrow
        from datetime import timedelta
        bangkok_target = bangkok_target + timedelta(days=1)
    
    # For scheduling, we'll use a wrapper that checks Bangkok time
    def scheduled_job():
        """Wrapper that checks if it's the right time in Bangkok before running."""
        current_bangkok = get_current_bangkok_time()
        target_hour, target_minute = map(int, time_str.split(':'))
        
        # Run if we're within 1 minute of the target time
        if (current_bangkok.hour == target_hour and 
            current_bangkok.minute == target_minute):
            run_news_fetch(db_path=db_path)
    
    # Schedule to check every minute
    schedule.every().minute.do(scheduled_job)
    
    print(f"📅 Scheduled daily news fetch at {time_str} (Bangkok time)")
    print(f"⏰ Current time: {now_bangkok.strftime('%Y-%m-%d %H:%M:%S')} (Bangkok time)")
    print(f"🔄 Running scheduler... (Press Ctrl+C to stop)\n")
    
    # Calculate next run time
    time_until_next = (bangkok_target - now_bangkok).total_seconds()
    hours = int(time_until_next // 3600)
    minutes = int((time_until_next % 3600) // 60)
    print(f"⏳ Next run in: {hours}h {minutes}m\n")
    
    return True


def run_scheduler():
    """Run the scheduler loop."""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def main():
    parser = argparse.ArgumentParser(
        description='Daily news scheduler - fetches and sends articles to Telegram',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once immediately (for testing)
  python3 scripts/daily_news_scheduler.py --once
  
  # Run as daemon (schedules daily at 7:00 AM Bangkok time)
  python3 scripts/daily_news_scheduler.py
  
  # Run with custom time
  python3 scripts/daily_news_scheduler.py --time "08:00"
  
  # Run with custom database path
  python3 scripts/daily_news_scheduler.py --db-path my_articles.db
        """
    )
    
    parser.add_argument('--once', action='store_true',
                       help='Run once immediately instead of scheduling')
    parser.add_argument('--time', default='07:00',
                       help='Time to run daily (HH:MM format, Bangkok time, default: 07:00)')
    parser.add_argument('--db-path', default='articles.db',
                       help='Path to SQLite database file (default: articles.db)')
    
    args = parser.parse_args()
    
    # Validate time format
    try:
        hour, minute = map(int, args.time.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time")
    except ValueError:
        print(f"❌ Error: Invalid time format '{args.time}'. Use HH:MM format (e.g., 07:00)", file=sys.stderr)
        sys.exit(1)
    
    if args.once:
        # Run once immediately
        print("🚀 Running news fetch once (testing mode)...\n")
        run_news_fetch(db_path=args.db_path)
    else:
        # Schedule daily runs
        if not schedule_daily_run(args.time, db_path=args.db_path):
            sys.exit(1)
        
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n\n⚠️  Scheduler stopped by user")
            sys.exit(0)


if __name__ == '__main__':
    main()

