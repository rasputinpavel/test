#!/usr/bin/env python3
"""
Script to manually add the "Published at" column to the articles database
if it doesn't exist, and migrate existing articles.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

def fix_database(db_path='articles.db'):
    """
    Ensure the "Published at" column exists and migrate articles.
    
    Args:
        db_path (str): Path to database file
    """
    # Resolve path
    db_file = Path(db_path)
    if not db_file.is_absolute():
        # Check in current directory and scripts directory
        if not db_file.exists():
            scripts_path = Path(__file__).parent / db_path
            if scripts_path.exists():
                db_file = scripts_path
            else:
                # Try in current working directory
                db_file = Path.cwd() / db_path
    
    if not db_file.exists():
        print(f"❌ Database file not found: {db_file}")
        return False
    
    print(f"📁 Opening database: {db_file}")
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute('PRAGMA table_info(articles)')
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if 'Published at' in columns:
        print("✅ Column 'Published at' already exists")
    else:
        print("📝 Adding 'Published at' column...")
        try:
            # Try with DEFAULT first
            cursor.execute('ALTER TABLE articles ADD COLUMN "Published at" TEXT DEFAULT "Unpublished"')
            conn.commit()
            print("✅ Column added with DEFAULT value")
        except sqlite3.OperationalError as e:
            print(f"⚠️  Could not add with DEFAULT: {e}")
            # Try without DEFAULT
            try:
                cursor.execute('ALTER TABLE articles ADD COLUMN "Published at" TEXT')
                conn.commit()
                # Set default for existing rows
                cursor.execute('UPDATE articles SET "Published at" = "Unpublished" WHERE "Published at" IS NULL')
                conn.commit()
                print("✅ Column added (set defaults manually)")
            except sqlite3.OperationalError as e2:
                print(f"❌ Failed to add column: {e2}")
                conn.close()
                return False
    
    # Migrate articles based on age
    print("\n📊 Migrating articles based on age...")
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    
    cursor.execute('SELECT ID, "Fetched at" FROM articles')
    articles = cursor.fetchall()
    
    published_count = 0
    unpublished_count = 0
    
    for article_id, fetched_at_str in articles:
        if not fetched_at_str:
            cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ('Unpublished', article_id))
            unpublished_count += 1
            continue
        
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at < one_day_ago:
                cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ('Published', article_id))
                published_count += 1
            else:
                cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ('Unpublished', article_id))
                unpublished_count += 1
        except (ValueError, TypeError) as e:
            cursor.execute('UPDATE articles SET "Published at" = ? WHERE ID = ?', ('Unpublished', article_id))
            unpublished_count += 1
    
    conn.commit()
    
    print(f"✅ Migration complete:")
    print(f"   📤 Published (older than 1 day): {published_count}")
    print(f"   📝 Unpublished (within 1 day): {unpublished_count}")
    
    # Verify final state
    cursor.execute('PRAGMA table_info(articles)')
    final_columns = [col[1] for col in cursor.fetchall()]
    print(f"\n✅ Final columns: {final_columns}")
    
    cursor.execute('SELECT "Published at", COUNT(*) FROM articles GROUP BY "Published at"')
    statuses = cursor.fetchall()
    print("\nStatus distribution:")
    for status, count in statuses:
        print(f"  {status}: {count}")
    
    conn.close()
    return True

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'articles.db'
    success = fix_database(db_path)
    sys.exit(0 if success else 1)

