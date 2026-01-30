#!/usr/bin/env python3
"""
Neptune - Website Content Extractor

Main entry point for the console application.
"""

import argparse
import sys
from pathlib import Path
import logging

from scraper import WebScraper
from categorizer import AICategorizer
from data_io import read_urls_from_csv, read_urls_with_metadata, sections_to_dataframe, write_output, create_summary_report
from cleaner import filter_dataframe, get_filter_summary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Extract section titles and content from websites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input urls.csv --output results.csv
  %(prog)s --input urls.csv --output results.xlsx --categorize
  %(prog)s --input urls.csv --output results.csv --categorize --summary
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input CSV file containing URLs'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output file path (.csv or .xlsx)'
    )
    
    parser.add_argument(
        '-c', '--categorize',
        action='store_true',
        help='Enable AI-powered categorization of sections'
    )
    
    parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='Generate an additional summary report'
    )
    
    parser.add_argument(
        '--url-column',
        default='url',
        help='Name of the column containing URLs (default: url)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='Disable data cleaning and filtering (keeps all scraped data)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    # Read URLs with metadata
    try:
        urls, url_metadata = read_urls_with_metadata(args.input, args.url_column)
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        sys.exit(1)
    
    if not urls:
        logger.error("No URLs found in input file")
        sys.exit(1)
    
    # Show metadata columns found
    metadata_cols = []
    if url_metadata and urls:
        first_url = urls[0]
        if first_url in url_metadata:
            metadata_cols = list(url_metadata[first_url].keys())
    
    print(f"\n{'='*60}")
    print(f"Neptune - Website Content Extractor")
    print(f"{'='*60}")
    print(f"Input file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"URLs to process: {len(urls)}")
    if metadata_cols:
        print(f"Source metadata columns: {', '.join(metadata_cols)}")
    print(f"AI categorization: {'Enabled' if args.categorize else 'Disabled'}")
    print(f"{'='*60}\n")
    
    # Initialize scraper
    scraper = WebScraper(timeout=args.timeout, delay=args.delay)
    
    # Scrape all URLs
    print("Extracting content from websites...")
    sections = scraper.scrape_urls(urls)
    print(f"Extracted {len(sections)} sections from {len(urls)} URLs\n")
    
    # Optionally categorize
    if args.categorize:
        print("Categorizing sections...")
        categorizer = AICategorizer()
        
        if categorizer.is_available():
            print("Using AI-powered categorization (OpenAI)")
        else:
            print("Using keyword-based fallback categorization")
            print("(Set OPENAI_API_KEY environment variable for AI categorization)")
        
        sections = categorizer.categorize_sections(sections)
        print("Categorization complete\n")
    
    # Convert to DataFrame with source metadata
    df = sections_to_dataframe(sections, url_metadata)
    original_count = len(df)
    
    # Apply data cleaning and filtering (unless disabled)
    if not args.no_filter:
        print("Cleaning and filtering data...")
        df = filter_dataframe(df)
        filter_summary = get_filter_summary(original_count, len(df))
        print(f"  Removed {filter_summary['removed_rows']} rows ({filter_summary['removal_percentage']}%)")
        print("Filtering complete\n")
    
    # Write output
    print(f"Writing results to {args.output}...")
    write_output(df, args.output)
    
    # Optionally create summary
    if args.summary and args.categorize:
        summary_path = Path(args.output)
        summary_file = summary_path.parent / f"{summary_path.stem}_summary{summary_path.suffix}"
        
        summary_df = create_summary_report(df)
        if not summary_df.empty:
            write_output(summary_df, str(summary_file))
            print(f"Summary report written to {summary_file}")
    
    # Print summary stats
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Total sections extracted: {len(sections)}")
    
    if args.categorize:
        category_counts = df['ai_category'].value_counts()
        print(f"\nSections by AI category:")
        for cat, count in category_counts.items():
            print(f"  {cat}: {count}")
    
    print(f"\nResults saved to: {args.output}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
