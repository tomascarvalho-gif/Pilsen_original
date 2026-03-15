"""
Downloader.py - Script to download financial data from SEC

This script:
1. Configures identity for SEC API access
2. Updates company list (company_tickers.json)
3. Downloads financial data (XBRL) from companies
4. Saves data as individual JSON files in xbrl_data_json/

Usage:
    python downloader.py [--years YEARS] [--limit N] [--log-file LOGFILE]

Examples:
    python downloader.py                              # Download last 2 years of all companies
    python downloader.py --limit 10                   # Test with 10 companies
    python downloader.py --log-file download.log      # Save logs to file

RECOMMENDED FOR OVERNIGHT RUN (500 companies, 10 years):
    python downloader.py --years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 --limit 500 --log-file download_$(date +%Y%m%d_%H%M%S).log

Features:
- Comprehensive logging with timestamps
- Rate limiting (respects EDGAR API limits)
- Automatic retry with exponential backoff
- Error tracking by type
- Progress tracking with ETA
- Graceful handling of interruptions
"""

import json
import os
import sys
import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import traceback

from dotenv import load_dotenv
load_dotenv()

# Importar funções necessárias do módulo info_picker_2
from info_picker_2 import (
    set_identity,
    update_company_list,
    SecTools_export_important_data,
    CompanyIns,
    CompanyData,
    FILE_PATH
)

# Import mapping variables from visualizer
# (needed to calculate ratios during download)
MAPPING_VARIABLE: Dict[str, str] = {
    "Total assets": "us-gaap_Assets",
    "Total liabilities": "us-gaap_Liabilities",
    "Cash": "us-gaap_CashAndCashEquivalentsAtCarryingValue",
    "Net income": "us-gaap_NetIncomeLoss",
    "Total shareholders' equity": "us-gaap_StockholdersEquity",
    "Shares diluted": "us-gaap_EarningsPerShareDiluted",
    "Shares basic": "us-gaap_EarningsPerShareBasic",
}

# Rate limiting constants (EDGAR allows ~10 requests/second)
EDGAR_RATE_LIMIT_DELAY = 0.12  # 120ms between requests = ~8 requests/second (safe margin)
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # Base delay in seconds for exponential backoff

# Statistics tracking
class DownloadStats:
    def __init__(self):
        self.start_time = datetime.now()
        self.companies_processed = 0
        self.companies_success = 0
        self.companies_failed = 0
        self.years_processed = 0
        self.years_success = 0
        self.years_failed = 0
        self.errors_by_type = {}
        self.rate_limit_hits = 0
        self.last_request_time = None
        
    def record_success(self, company: str, year: int):
        self.companies_success += 1
        self.years_success += 1
        
    def record_failure(self, company: str, year: int, error_type: str, error_msg: str):
        self.companies_failed += 1
        self.years_failed += 1
        if error_type not in self.errors_by_type:
            self.errors_by_type[error_type] = []
        self.errors_by_type[error_type].append({
            "company": company,
            "year": year,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        
    def record_rate_limit(self):
        self.rate_limit_hits += 1
        
    def get_elapsed_time(self) -> timedelta:
        return datetime.now() - self.start_time
        
    def get_summary(self) -> Dict:
        elapsed = self.get_elapsed_time()
        total_companies = self.companies_success + self.companies_failed
        total_years = self.years_success + self.years_failed
        
        return {
            "elapsed_time": str(elapsed),
            "companies_total": total_companies,
            "companies_success": self.companies_success,
            "companies_failed": self.companies_failed,
            "companies_success_rate": (self.companies_success / total_companies * 100) if total_companies > 0 else 0,
            "years_total": total_years,
            "years_success": self.years_success,
            "years_failed": self.years_failed,
            "years_success_rate": (self.years_success / total_years * 100) if total_years > 0 else 0,
            "rate_limit_hits": self.rate_limit_hits,
            "errors_by_type": {k: len(v) for k, v in self.errors_by_type.items()}
        }

# Global stats instance
stats = DownloadStats()


def setup_logging(log_file: Optional[str] = None, log_level: int = logging.INFO):
    """
    Configure logging with timestamps and file output.
    
    Args:
        log_file: Optional path to log file. If None, logs only to console.
        log_level: Logging level (default: INFO)
    """
    # Create formatter with timestamp
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)-8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")
    
    return logger


def rate_limit_delay():
    """
    Enforce rate limiting between requests to EDGAR API.
    """
    global stats
    if stats.last_request_time:
        elapsed = (datetime.now() - stats.last_request_time).total_seconds()
        if elapsed < EDGAR_RATE_LIMIT_DELAY:
            sleep_time = EDGAR_RATE_LIMIT_DELAY - elapsed
            time.sleep(sleep_time)
    stats.last_request_time = datetime.now()


def setup_sec_identity():
    """
    Configure identity for SEC API access.
    SEC requires identification (name and email) to access their data.
    Reads SEC_IDENTITY from the environment (or .env file).
    """
    logging.info("Setting up SEC identity...")
    identity = os.environ.get("SEC_IDENTITY")
    if not identity:
        raise EnvironmentError(
            "SEC_IDENTITY is not set. Add it to your .env file:\n"
            "  SEC_IDENTITY=Your Name your@email.com"
        )
    try:
        set_identity(identity)
        logging.info("SEC identity configured successfully")
    except Exception as e:
        logging.error(f"Failed to set SEC identity: {e}", exc_info=True)
        raise


def update_companies():
    """
    Update company list from SEC.
    Downloads company_tickers.json from SEC website.
    """
    logging.info("Updating company list from SEC...")
    try:
        update_company_list()
        logging.info("Company list updated successfully")
    except Exception as e:
        logging.error(f"Failed to update company list: {e}", exc_info=True)
        raise


def load_companies() -> CompanyData:
    """
    Load saved company list from local file.
    
    Returns:
        CompanyData: Object containing all companies
    """
    logging.info("Loading company list from local file...")
    companies = CompanyData()
    companies.load_saved_companies()
    logging.info(f"Loaded {len(companies.companies)} companies")
    return companies


def download_company_year_with_retry(
    company: CompanyIns,
    companies_data: CompanyData,
    year: int,
    mapping_variables: Dict[str, str]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Download data for a company and year with retry logic.
    INCLUDES SMART RESUME: Skips if file already exists.
    """
    ticker = company.ticker
    cik = company.cik
    
    # --- SMART RESUME CHECK START ---
    # Check if we already have this year downloaded to save time
    json_dir = "xbrl_data_json"
    ticker_dir = os.path.join(json_dir, ticker)
    
    if os.path.exists(ticker_dir):
        try:
            # Check existing files in the ticker's folder
            existing_files = os.listdir(ticker_dir)
            for f in existing_files:
                # Logic matches your verify_downloads: checks for year in filename
                if f"_{year}" in f and f.endswith(".json"):
                    logging.info(f"⏭️ Skipping {ticker} {year} (Found existing file: {f})")
                    return True, None, None
        except OSError:
            pass # If folder read fails, just proceed to download
    # --- SMART RESUME CHECK END ---

    for attempt in range(MAX_RETRIES):
        try:
            # Rate limiting
            rate_limit_delay()
            
            logging.debug(f"Attempt {attempt + 1}/{MAX_RETRIES} for {ticker} {year}")
            
            # Download data
            updated_company = SecTools_export_important_data(
                company=company,
                existing_data=companies_data,
                year=year,
                mapping_variables=mapping_variables
            )
            
            if updated_company:
                companies_data.companies[cik] = updated_company
                logging.info(f"Successfully downloaded {ticker} {year}")
                return True, None, None
            else:
                # No data found (not necessarily an error)
                logging.warning(f"No data found for {ticker} in {year}")
                return False, "NO_DATA", f"No filings found for {ticker} in {year}"
                
        except KeyboardInterrupt:
            # Don't retry on keyboard interrupt
            raise
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check for rate limiting errors
            if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                stats.record_rate_limit()
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                logging.warning(f"Rate limit hit for {ticker} {year}. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            
            # Check for HTTP errors
            if "403" in error_msg or "forbidden" in error_msg.lower():
                logging.error(f"HTTP 403 Forbidden for {ticker} {year}: {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                    logging.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return False, "HTTP_403", error_msg
            
            if "404" in error_msg or "not found" in error_msg.lower():
                logging.warning(f"HTTP 404 Not Found for {ticker} {year}: {error_msg}")
                return False, "HTTP_404", error_msg
            
            if "500" in error_msg or "502" in error_msg or "503" in error_msg:
                logging.warning(f"Server error for {ticker} {year}: {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                    logging.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            
            # Other errors
            logging.error(f"Error downloading {ticker} {year} (attempt {attempt + 1}/{MAX_RETRIES}): {error_type}: {error_msg}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                logging.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed after {MAX_RETRIES} attempts for {ticker} {year}")
                return False, error_type, error_msg
    
    return False, "MAX_RETRIES_EXCEEDED", f"Failed after {MAX_RETRIES} attempts"


def download_company_data(
    company: CompanyIns,
    companies_data: CompanyData,
    years: List[int],
    mapping_variables: Dict[str, str]
) -> bool:
    """
    Download financial data for a specific company.
    
    Args:
        company: CompanyIns object with company information
        companies_data: Data for all companies (for updates)
        years: List of years to download
        mapping_variables: Variable mapping for data extraction
    
    Returns:
        bool: True if success, False if failed
    """
    ticker = company.ticker
    cik = company.cik
    title = company.title
    
    logging.info(f"{'='*80}")
    logging.info(f"Processing: {title} [{ticker}] (CIK: {cik})")
    logging.info(f"{'='*80}")
    
    company_success = True
    
    try:
        for year in years:
            logging.info(f"Downloading {ticker} data for year {year}...")
            
            success, error_type, error_msg = download_company_year_with_retry(
                company=company,
                companies_data=companies_data,
                year=year,
                mapping_variables=mapping_variables
            )
            
            if success:
                stats.record_success(ticker, year)
            else:
                stats.record_failure(ticker, year, error_type or "UNKNOWN", error_msg or "Unknown error")
                if error_type != "NO_DATA":  # NO_DATA is expected for some companies/years
                    company_success = False
        
        return company_success
        
    except KeyboardInterrupt:
        logging.warning(f"Download interrupted for {ticker}")
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logging.error(f"Fatal error downloading {ticker}: {error_type}: {error_msg}", exc_info=True)
        stats.record_failure(ticker, 0, error_type, error_msg)
        return False


def calculate_eta(elapsed_time: timedelta, completed: int, total: int) -> Optional[timedelta]:
    """Calculate estimated time remaining."""
    if completed == 0:
        return None
    avg_time_per_item = elapsed_time / completed
    remaining_items = total - completed
    return avg_time_per_item * remaining_items


def download_all_companies(
    years: Optional[List[int]] = None,
    limit: Optional[int] = None
):
    """
    Download financial data for all (or limited) companies.
    
    Args:
        years: List of years to download. If None, uses last 2 years
        limit: Maximum number of companies to download. If None, downloads all
    """
    global stats
    
    # Default years: last 10 years
    if years is None:
        current_year = datetime.now().year
        years = list(range(current_year - 9, current_year + 1))
    
    logging.info(f"Configuration:")
    logging.info(f"  Years to download: {years}")
    if limit:
        logging.info(f"  Company limit: {limit}")
    else:
        logging.info(f"  Downloading ALL companies")
    logging.info(f"  Rate limit delay: {EDGAR_RATE_LIMIT_DELAY}s between requests")
    logging.info(f"  Max retries per download: {MAX_RETRIES}")
    
    # Load companies
    companies_data = load_companies()
    
    # Statistics
    total_companies = len(companies_data.companies)
    companies_to_process = min(limit, total_companies) if limit else total_companies
    total_years_to_download = companies_to_process * len(years)
    
    logging.info(f"Statistics:")
    logging.info(f"  Total companies available: {total_companies}")
    logging.info(f"  Companies to process: {companies_to_process}")
    logging.info(f"  Total year downloads: {total_years_to_download}")
    logging.info(f"  Estimated time: ~{total_years_to_download * 3 / 60:.1f} minutes (at 3s per download)")
    
    # Process companies
    companies_list = list(companies_data.companies.items())
    
    for idx, (cik, company) in enumerate(companies_list, 1):
        # Check limit
        if limit and idx > limit:
            logging.info(f"Company limit ({limit}) reached. Stopping.")
            break
        
        # Progress logging
        stats.companies_processed = idx
        elapsed = stats.get_elapsed_time()
        eta = calculate_eta(elapsed, idx, companies_to_process)
        
        logging.info(f"\n{'='*80}")
        logging.info(f"Progress: {idx}/{companies_to_process} companies ({idx/companies_to_process*100:.1f}%)")
        logging.info(f"Elapsed: {elapsed}")
        if eta:
            logging.info(f"ETA: {eta} (~{eta.total_seconds()/3600:.1f} hours)")
        logging.info(f"Success rate: {stats.companies_success}/{idx} companies ({stats.companies_success/idx*100:.1f}%)")
        logging.info(f"{'='*80}")
        
        # Download company data
        try:
            success = download_company_data(
                company=company,
                companies_data=companies_data,
                years=years,
                mapping_variables=MAPPING_VARIABLE
            )
            
            if success:
                logging.info(f"Company {idx}/{companies_to_process} completed successfully")
            else:
                logging.warning(f"Company {idx}/{companies_to_process} completed with errors")
                
        except KeyboardInterrupt:
            logging.warning(f"\nDownload interrupted by user at company {idx}/{companies_to_process}")
            logging.info("Progress saved. You can resume later.")
            raise
        except Exception as e:
            logging.error(f"Unexpected error processing company {idx}: {e}", exc_info=True)
            stats.record_failure(company.ticker, 0, "UNEXPECTED_ERROR", str(e))
    
    # Final summary
    summary = stats.get_summary()
    logging.info(f"\n{'='*80}")
    logging.info("FINAL SUMMARY")
    logging.info(f"{'='*80}")
    logging.info(f"Total elapsed time: {summary['elapsed_time']}")
    logging.info(f"\nCompanies:")
    logging.info(f"  Total processed: {summary['companies_total']}")
    logging.info(f"  Successful: {summary['companies_success']}")
    logging.info(f"  Failed: {summary['companies_failed']}")
    logging.info(f"  Success rate: {summary['companies_success_rate']:.1f}%")
    logging.info(f"\nYear Downloads:")
    logging.info(f"  Total: {summary['years_total']}")
    logging.info(f"  Successful: {summary['years_success']}")
    logging.info(f"  Failed: {summary['years_failed']}")
    logging.info(f"  Success rate: {summary['years_success_rate']:.1f}%")
    logging.info(f"\nRate Limiting:")
    logging.info(f"  Rate limit hits: {summary['rate_limit_hits']}")
    logging.info(f"\nErrors by type:")
    for error_type, count in summary['errors_by_type'].items():
        logging.info(f"  {error_type}: {count}")
    logging.info(f"{'='*80}")
    
    # Log detailed errors if any
    if stats.errors_by_type:
        logging.info("\nDetailed error log:")
        for error_type, errors in stats.errors_by_type.items():
            logging.info(f"\n{error_type} errors ({len(errors)}):")
            for error in errors[:10]:  # Show first 10 of each type
                logging.info(f"  {error['company']} {error['year']}: {error['error']}")
            if len(errors) > 10:
                logging.info(f"  ... and {len(errors) - 10} more")


def verify_downloads():
    """
    Verify how many JSON files were downloaded.
    """
    json_dir = "xbrl_data_json"
    
    if not os.path.exists(json_dir):
        logging.warning(f"Directory {json_dir} does not exist.")
        return
    
    total_files = 0
    companies_with_data = 0
    files_by_year = {}
    
    for ticker_folder in os.listdir(json_dir):
        folder_path = os.path.join(json_dir, ticker_folder)
        if os.path.isdir(folder_path):
            files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
            if files:
                companies_with_data += 1
                total_files += len(files)
                
                # Count by year
                for file in files:
                    try:
                        # Extract year from filename (format: TICKER_YYYY-MM-DD.json)
                        year = int(file.split('_')[1].split('-')[0])
                        files_by_year[year] = files_by_year.get(year, 0) + 1
                    except (IndexError, ValueError):
                        pass
    
    logging.info(f"\nDownload Verification:")
    logging.info(f"  Companies with data: {companies_with_data}")
    logging.info(f"  Total JSON files: {total_files}")
    if files_by_year:
        logging.info(f"  Files by year:")
        for year in sorted(files_by_year.keys()):
            logging.info(f"    {year}: {files_by_year[year]} files")


def main():
    """
    Main function for the downloader.
    """
    parser = argparse.ArgumentParser(
        description="Download financial data from SEC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Download last 2 years of all companies
  %(prog)s --years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 --limit 500
  %(prog)s --limit 5                          # Test with 5 companies
  %(prog)s --log-file download.log             # Save logs to file
  %(prog)s --log-level DEBUG                  # Verbose logging
        """
    )
    
    parser.add_argument(
        '--years',
        type=int,
        nargs='+',
        help='Years to download (e.g., 2020 2021 2022). Default: last 10 years'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of companies to download (useful for testing)'
    )
    
    parser.add_argument(
        '--skip-setup',
        action='store_true',
        help='Skip initial setup (use existing data)'
    )
    
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing downloads, do not download anything'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Path to log file (default: console only). Recommended for overnight runs.'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(log_file=args.log_file, log_level=log_level)
    
    logging.info("="*80)
    logging.info("SEC FINANCIAL DATA DOWNLOADER")
    logging.info("="*80)
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.log_file:
        logging.info(f"Log file: {args.log_file}")
    logging.info(f"Log level: {args.log_level}")
    logging.info("="*80)
    
    # Verify-only mode
    if args.verify_only:
        verify_downloads()
        return
    
    # Initial setup
    if not args.skip_setup:
        setup_sec_identity()
        update_companies()
    else:
        logging.info("Skipping initial setup (--skip-setup)")
    
    # Download
    try:
        download_all_companies(
            years=args.years,
            limit=args.limit
        )
    except KeyboardInterrupt:
        logging.warning("\nDownload interrupted by user (Ctrl+C)")
        logging.info("Progress saved. You can resume later.")
        summary = stats.get_summary()
        logging.info(f"Processed {summary['companies_total']} companies before interruption")
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Final verification
        verify_downloads()
        logging.info(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("Download session completed!")
        logging.info("Data saved in: xbrl_data_json/")


if __name__ == "__main__":
    main()
