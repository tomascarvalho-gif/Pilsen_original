# OP-Screener

Financial data analysis system for SEC filings with interactive visualization.

## Overview

OP-Screener downloads financial data from the SEC (Securities and Exchange Commission) and provides an interactive web-based dashboard for analysis and comparison of company financials.

The system is separated into two independent modules:

- **Downloader**: CLI tool for data acquisition
- **Visualizer**: Web application for data analysis

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd OP-screener

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Data

```bash
# Test with 5 companies
python downloader.py --limit 5 --years 2023 2024

# Download specific years
python downloader.py --years 2022 2023 2024

# Download all companies (time-consuming)
python downloader.py
```

### 3. Visualize Data

```bash
# Start web application
python visualizer.py

# Access at: http://127.0.0.1:8050/
```

## Features

### Data Acquisition (downloader.py)

- Downloads 10-Q and 10-K filings from SEC EDGAR
- Parses XBRL financial statements
- Calculates financial ratios (ROE, P/E, D/E, etc.)
- Integrates Yahoo Finance stock prices
- Saves structured JSON files
- Command-line interface with progress tracking

### Data Visualization (visualizer.py)

- Interactive web dashboard (Dash/Plotly)
- Multi-company comparison
- Market index overlays (S&P 500, Dow Jones)
- Time series analysis
- Sortable/filterable data tables
- Logarithmic and linear scaling

### Available Metrics

**Base Variables (GAAP):**

- Total assets
- Total liabilities
- Cash and cash equivalents
- Net income
- Shareholders' equity

**Computed Ratios:**

- ROE (Return on Equity)
- P/E (Price to Earnings)
- P/FCF (Price to Free Cash Flow)
- P/CF (Price to Cash Flow)
- D/E (Debt to Equity)
- Pretax Profit Margin

## Project Structure

```
OP-screener/
├── downloader.py              # Data acquisition CLI
├── visualizer.py              # Web visualization app
├── info_picker_2.py           # SEC API integration
├── helper.py                  # Utility functions
├── indicators.py              # Financial ratio calculations
├── requirements.txt           # Python dependencies
├── test_separation.py         # Test suite
├── TECHNICAL_DOCUMENTATION.md # Detailed technical docs
├── company_tickers.json       # Company list (generated)
└── xbrl_data_json/            # Downloaded data (generated)
```

## Usage Examples

### Download Commands

```bash
# Test with limited companies
python downloader.py --limit 10

# Download specific years
python downloader.py --years 2020 2021 2022

# Verify downloaded data
python downloader.py --verify-only

# Skip setup (use existing config)
python downloader.py --skip-setup --years 2024
```

### Available Options

- `--years`: Specify years to download (e.g., `--years 2020 2021`)
- `--limit`: Limit number of companies (useful for testing)
- `--skip-setup`: Skip initial configuration
- `--verify-only`: Check downloaded data without downloading

## Architecture

### Separation of Concerns

The project follows the Single Responsibility Principle:

**Before (Monolithic):**

- Single file mixed download and visualization
- Slow startup due to automatic downloads
- Difficult to test and maintain

**After (Separated):**

- Independent download and visualization modules
- Fast visualizer startup (reads local files only)
- Clear interfaces and responsibilities

### Data Flow

```
SEC API → downloader.py → JSON files → visualizer.py → Browser
```

1. Downloader fetches data from SEC and Yahoo Finance
2. Data is processed and saved as JSON
3. Visualizer reads JSON files and generates interactive graphs
4. User interacts with web interface in browser

## Testing

Run the test suite to verify the implementation:

```bash
python test_separation.py
```

Expected output: 5/5 tests passed

## Performance

### Download Performance

- ~3-5 seconds per company per year
- SEC API rate limit: ~10 requests/second
- Full download (all companies, 10 years): 15-20 hours

### Visualizer Performance

- Startup time: ~1 second
- Graph generation: <1 second
- No network requests (local data only)

### Storage Requirements

- ~20-50 KB per filing (JSON)
- ~2 GB for 500 companies, 10 years

## Dependencies

Key dependencies:

- pandas (2.2.0): Data manipulation
- dash (2.18.2): Web framework
- plotly (5.24.1): Interactive graphs
- edgartools (2.34.2): SEC API client
- yfinance (0.2.48): Yahoo Finance API
- beautifulsoup4 (4.12.3): HTML parsing

See `requirements.txt` for complete list.

## Troubleshooting

### No data for selected companies

**Solution:** Run `python downloader.py --limit 10` first

### Missing company_tickers.json

**Solution:** Run `python downloader.py` (creates file automatically)

### Slow downloads

**Cause:** SEC API rate limiting  
**Solution:** Normal behavior; use `--limit` for testing

### Empty graphs in visualizer

**Solution:** Ensure data exists in `xbrl_data_json/` directory

## Contributing

This is an academic project. For questions or issues, contact the developer.

## License

See LICENSE file for details.

## Contact

**Developer:** Tomas de Freitas Carvalho  
**Email:** tomasdfc@mac.com  
**Date:** January 2026

## Documentation

For detailed technical information, see `TECHNICAL_DOCUMENTATION.md`.

## Acknowledgments

- SEC for providing public financial data
- edgartools library for SEC API integration
- Dash/Plotly for visualization framework
- Yahoo Finance for stock price data
