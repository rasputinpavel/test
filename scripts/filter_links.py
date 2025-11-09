#!/usr/bin/env python3
"""
Function to filter links by a given substring or glob pattern.
"""

import fnmatch


def filter_links(links, pattern, case_sensitive=False, use_glob=False):
    """
    Filter links that match a given substring or glob pattern.
    
    Args:
        links (list): List of URL strings to filter
        pattern (str): Substring or glob pattern to match (e.g., 'github.com' or '*/2025/*')
        case_sensitive (bool, optional): Whether the search should be case-sensitive.
                                        Defaults to False.
        use_glob (bool, optional): Whether to treat pattern as a glob pattern (supports * and ?).
                                  If False, uses simple substring matching. Defaults to False.
                                  Auto-detected if pattern contains * or ?.
    
    Returns:
        list: List of links that match the pattern
    """
    # Auto-detect glob pattern if it contains wildcards
    if not use_glob and ('*' in pattern or '?' in pattern):
        use_glob = True
    
    if use_glob:
        if case_sensitive:
            return [link for link in links if fnmatch.fnmatch(link, pattern)]
        else:
            return [link for link in links if fnmatch.fnmatchcase(link.lower(), pattern.lower())]
    else:
        # Simple substring matching
        if case_sensitive:
            return [link for link in links if pattern in link]
        else:
            pattern_lower = pattern.lower()
            return [link for link in links if pattern_lower in link.lower()]


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Filter links by substring or glob pattern',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 filter_links.py 'github.com' https://example.com https://github.com/user
  python3 extract_links.py page.html | python3 filter_links.py '*/2025/*'
  python3 filter_links.py '*/2025/*' -o output.txt < links.txt
        """
    )
    parser.add_argument('pattern', help='Substring or glob pattern (e.g., "github.com" or "*/2025/*")')
    parser.add_argument('links', nargs='*', help='Links to filter (if not provided, reads from stdin)')
    parser.add_argument('-o', '--output', help='Output file (if not provided, prints to stdout)')
    parser.add_argument('-c', '--case-sensitive', action='store_true', help='Case-sensitive matching')
    
    args = parser.parse_args()
    
    # Get links from arguments or stdin
    links = args.links if args.links else []
    if not links:
        links = [line.strip() for line in sys.stdin if line.strip()]
    
    filtered = filter_links(links, args.pattern, case_sensitive=args.case_sensitive)
    
    # Write to file or stdout
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            for link in filtered:
                f.write(link + '\n')
    else:
        # Handle broken pipe gracefully when piping
        try:
            for link in filtered:
                print(link)
        except BrokenPipeError:
            # Pipe was closed (e.g., head command, or next command in pipeline exited)
            pass

