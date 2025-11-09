# 🔧 Utility Scripts

Useful scripts for automating checks and calculations.

## 📊 check_range.py

Checks if numbers fall within specified ranges. Useful for health test analysis, financial metrics, and other numerical data.

### Usage:

```bash
python3 scripts/check_range.py [value] [min] [max] [value] [min] [max] ...
```

### Examples:

**Blood tests:**

```bash
# Cholesterol (normal 120-200), Sugar (normal 70-100), Blood pressure (normal 80-120)
python3 scripts/check_range.py 185 120 200 92 70 100 85 80 120
```

**Budget categories:**

```bash
# Food expenses (budget 500-700), Entertainment (budget 200-300)
python3 scripts/check_range.py 650 500 700 250 200 300
```

**Result:**

```
🔍 Range Check:
==================================================
   185.0 | [ 120.0 -  200.0] | ✅ In range
    92.0 | [  70.0 -  100.0] | ✅ In range
    85.0 | [  80.0 -  120.0] | ✅ In range
==================================================
```

### Why is this needed?

LLMs often make mistakes when comparing numbers. This script provides precise mathematical results that can be used in analysis.

## 🔗 extract_links.py

Extracts all links from HTML content. Simple and minimal implementation.

### Usage:

```bash
# Extract links from HTML file
python3 scripts/extract_links.py <html_file> [base_url]

# Or use as a Python module
from scripts.extract_links import extract_links
links = extract_links(html_content, base_url="https://example.com")
```

### Example:

```bash
python3 scripts/extract_links.py page.html https://example.com
```

**Note:** Requires `beautifulsoup4` library. Install with: `pip install beautifulsoup4`

## 📄 fetch_html_text.py

Fetches HTML page text by downloading from a URL or reading from a local file. Extracts and returns clean text content from HTML (removes scripts, styles, and excessive whitespace).

### Usage:

```bash
# Fetch text from URL
python3 scripts/fetch_html_text.py <url>

# Fetch text from local HTML file
python3 scripts/fetch_html_text.py <html_file>

# Or use as a Python module
from scripts.fetch_html_text import fetch_html_text
text = fetch_html_text("https://example.com")
# or
text = fetch_html_text("page.html")
```

### Examples:

```bash
# Fetch text from a website
python3 scripts/fetch_html_text.py https://example.com

# Fetch text from a local HTML file
python3 scripts/fetch_html_text.py page.html
```

### Features:

- Supports both URLs (http:// and https://) and local file paths
- Automatically extracts text content from HTML
- Removes script and style elements
- Cleans up excessive whitespace
- Handles encoding errors gracefully
- Provides clear error messages for common issues

**Note:** Requires `beautifulsoup4` library. Install with: `pip install beautifulsoup4`

## 📚 fetch_articles_batch.py

Batch fetches articles from multiple URLs listed in a file. Uses `fetch_html_text.py` to download and extract text from each URL, saving them to individual files.

### Usage:

```bash
# Fetch all URLs from a file (saves to 'articles' directory)
python3 scripts/fetch_articles_batch.py <urls_file>

# Specify custom output directory
python3 scripts/fetch_articles_batch.py <urls_file> <output_dir>
```

### Examples:

```bash
# Fetch all articles from filtered_links.txt
python3 scripts/fetch_articles_batch.py scripts/filtered_links.txt

# Save to custom directory
python3 scripts/fetch_articles_batch.py scripts/filtered_links.txt my_articles/
```

### Features:

- Reads URLs from a text file (one URL per line)
- Automatically generates safe filenames from URLs
- Saves each article to a separate text file
- Shows progress for each URL
- Provides summary with success/failure counts
- Skips empty lines and comments (lines starting with #)

### Output:

- Creates an `articles/` directory (or uses specified directory)
- Each article is saved as a separate `.txt` file
- Filenames are derived from the URL slug
- Shows character count and line count for each article

**Note:** Requires `beautifulsoup4` library. Install with: `pip install beautifulsoup4`

## Ideas for other scripts:

* `calculate_bmi.py` - body mass index calculation
* `currency_convert.py` - currency conversion
* `compound_interest.py` - compound interest calculation
* `health_metrics.py` - healthy range calculations by age
