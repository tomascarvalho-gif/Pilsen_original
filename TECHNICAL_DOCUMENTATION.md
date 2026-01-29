# OP-Screener: Technical Documentation

## Project Overview

This project implements a financial data analysis system that downloads SEC (Securities and Exchange Commission) filings and provides interactive visualization capabilities. The codebase has been restructured to separate data acquisition from visualization, following the Single Responsibility Principle.

## Architecture

### System Components

The system consists of two primary modules:

1. **Data Acquisition Module** (`downloader.py`): Command-line interface for downloading financial data
2. **Visualization Module** (`visualizer.py`): Web-based interactive dashboard for data analysis

### Supporting Modules

- **`info_picker_2.py`**: SEC API integration and XBRL parsing functions
- **`helper.py`**: Utility functions for data manipulation and formatting
- **`indicators.py`**: Financial ratio calculation engine

## Module Specifications

### 1. Data Acquisition Module (downloader.py)

#### Purpose
Standalone CLI tool for downloading and processing SEC financial filings.

#### Key Functions

**`setup_sec_identity()`**
- Configures SEC API credentials
- Required for API access compliance

**`update_companies()`**
- Downloads latest company ticker list from SEC
- Updates `company_tickers.json`

**`load_companies()`**
- Loads company data from local cache
- Returns: `CompanyData` object

**`download_company_data(company, companies_data, years, mapping_variables)`**
- Downloads financial filings for a specific company
- Parameters:
  - `company`: CompanyIns object
  - `companies_data`: Global company data structure
  - `years`: List of years to download
  - `mapping_variables`: GAAP variable mapping dictionary
- Returns: Boolean indicating success/failure

**`download_all_companies(years, limit)`**
- Iterates through company list and downloads data
- Parameters:
  - `years`: Optional list of years (default: last 2 years)
  - `limit`: Optional limit on number of companies
- Implements progress tracking and error handling

**`verify_downloads()`**
- Validates downloaded data
- Reports statistics on available filings

#### Command-Line Interface

```bash
# Basic usage
python downloader.py

# With options
python downloader.py --years 2020 2021 2022 --limit 50

# Verification mode
python downloader.py --verify-only
```

**Available Options:**
- `--years`: Specify years to download (e.g., `--years 2020 2021`)
- `--limit`: Limit number of companies to process
- `--skip-setup`: Skip initial configuration (use existing data)
- `--verify-only`: Run verification without downloading

#### Output Structure

Data is saved in the following structure:

```
xbrl_data_json/
├── AAPL/
│   ├── AAPL_2024-03-30.json
│   ├── AAPL_2023-12-30.json
│   └── ...
├── MSFT/
│   └── ...
└── [other tickers]/
```

Each JSON file contains:
- `balance_sheet`: Balance sheet data
- `income`: Income statement data
- `cashflow`: Cash flow statement data
- `date`: Filing date
- `ticker`: Company ticker symbol
- `base`: Extracted GAAP variables (29 items)
- `computed`: Calculated financial ratios (6 items)
- `yf_value`: Stock price from Yahoo Finance (optional)

### 2. Visualization Module (visualizer.py)

#### Purpose
Interactive web application built with Dash/Plotly for financial data visualization.

#### Architecture
- Framework: Dash (Flask-based)
- Rendering: Plotly graphs
- Styling: Dash Bootstrap Components (CYBORG theme)
- Data Source: Local JSON files only (no downloading)

#### Key Functions

**`load_summary_table(selected_variables)`**
- Loads aggregated data table
- Parameters:
  - `selected_variables`: List of variables to include
- Returns: pandas DataFrame

**`generate_graph(selected_ciks, selected_variables, selected_indexes, start_year, end_year, use_yahoo)`**
- Generates interactive Plotly figure
- Parameters:
  - `selected_ciks`: List of company CIKs
  - `selected_variables`: Financial variables to plot
  - `selected_indexes`: Market indexes to overlay
  - `start_year`, `end_year`: Date range
  - `use_yahoo`: Boolean for Yahoo Finance integration
- Returns: plotly.graph_objects.Figure

**`build_company_dropdown_options()`**
- Constructs dropdown options including companies and indexes
- Returns: List of option dictionaries

**`expand_selected_values(values)`**
- Expands index shortcuts (e.g., ^SPX) into constituent CIKs
- Handles S&P 500 and Dow Jones presets
- Returns: List of CIKs

#### User Interface Components

1. **Company Selector**: Multi-select dropdown with ~13,000 companies
2. **Index Selector**: S&P 500, Dow Jones Industrial Average
3. **Variable Selector**: Grouped dropdown (Base, Computed, Special)
4. **Date Range**: Year input fields
5. **Data Table**: Interactive, sortable, filterable
6. **Graph Display**: Log-scale primary axis, linear secondary axis for indexes

#### Execution

```bash
python visualizer.py
# Access at: http://127.0.0.1:8050/
```

### 3. SEC Integration Module (info_picker_2.py)

#### Core Functions

**`SecTools_export_important_data(company, existing_data, year, mapping_variables)`**
- Primary function for downloading SEC filings
- Fetches 10-Q and 10-K forms via edgartools library
- Processes XBRL data
- Calculates financial ratios
- Saves to JSON
- Returns: Updated CompanyIns object

**`save_financials_as_json(financials_file, ticker, reporting_date, variable_mapping, yf_value)`**
- Serializes financial statements to JSON
- Integrates Yahoo Finance price data
- Triggers ratio computation
- Returns: File path

**`download_SP500_tickers()` / `download_DJI_tickers()`**
- Scrapes Wikipedia for index constituents
- Implements 24-hour caching
- Handles HTTP 403 errors gracefully
- Returns: List of ticker symbols

**`yf_download_price(ticker, date, file_path, window_days)`**
- Downloads stock price from Yahoo Finance
- Uses nearest trading day within window
- Persists to JSON
- Returns: Float price or None

#### Data Classes

**`CompanyIns`**
```python
class CompanyIns:
    cik: str          # Central Index Key
    ticker: str       # Stock symbol
    title: str        # Company name
    years: dict       # Year -> List[CompanyFinancials]
```

**`CompanyData`**
```python
class CompanyData:
    companies: Dict[str, CompanyIns]
    
    def load_saved_companies()
    def save_companies()
    def update_companies(new_data)
```

**`CompanyFinancials`**
```python
class CompanyFinancials:
    date: datetime           # Report date
    financials: Financials   # edgar.Financials object
    location: str            # JSON file path
    json_data: dict          # Cached data
```

### 4. Utility Module (helper.py)

#### Functions

**`human_format(num)`**
- Converts numbers to human-readable format (K, M, B, T)
- Example: `1000000` -> `"1.00M"`

**`safe_div(num, den)`**
- Division with zero handling
- Returns: Float or None

**`find_variables_and_sheets_by_concepts(json_file_or_dict, concepts, exclude_abstract, sheet_order)`**
- Resolves XBRL concepts across financial statements
- Single-pass lookup algorithm
- Returns: Dict mapping concept to (sheet_name, variable_name)

**`get_variables_from_json_dict(json_file_or_dict, requests, return_with_column)`**
- Extracts multiple variables from a filing
- Parameters:
  - `requests`: Dict of {out_key: (sheet, variable)}
  - `return_with_column`: Boolean for including column metadata
- Returns: Dict of extracted values

### 5. Financial Indicators Module (indicators.py)

#### Ratio Calculation Functions

**`calculate_ROE(variables)`**
- Return on Equity = Net Income / Shareholders' Equity
- Returns: Percentage

**`calculate_PE(variables, file_or_json, stock_price)`**
- Price to Earnings = Price per Share / EPS
- Uses reported EPS or calculates from Net Income / Shares
- Returns: Float ratio

**`calculate_PFCF(variables, file_or_json, stock_price)`**
- Price to Free Cash Flow
- FCF = Operating Cash Flow - CapEx
- Returns: Float ratio

**`calculate_PCF(variables, file_or_json, stock_price)`**
- Price to Cash Flow = Price / (Operating Cash Flow per Share)
- Returns: Float ratio

**`calculate_debt_eq_ratio(variables)`**
- Debt to Equity = Total Debt / Shareholders' Equity
- Handles component summation if total not reported
- Returns: Float ratio

**`calculate_pretax_margin(variables)`**
- Pretax Profit Margin = Income Before Tax / Revenue * 100
- Returns: Percentage

**`compute_ratios(file, variable_mapping, stock_price)`**
- Master function computing all ratios
- Parameters:
  - `file`: JSON file path or dict
  - `variable_mapping`: GAAP variable mapping
  - `stock_price`: Optional price for P/E, P/FCF, P/CF
- Returns: Dict with 'base' and 'computed' sections

#### XBRL Concept Mapping

The module uses US-GAAP taxonomy concepts:

**Base Variables:**
- `us-gaap_Assets`
- `us-gaap_Liabilities`
- `us-gaap_CashAndCashEquivalentsAtCarryingValue`
- `us-gaap_NetIncomeLoss`
- `us-gaap_StockholdersEquity`
- `us-gaap_EarningsPerShareDiluted`
- `us-gaap_EarningsPerShareBasic`

**Computed Variables:**
- ROE (Return on Equity)
- P/E (Price to Earnings)
- P/FCF (Price to Free Cash Flow)
- P/CF (Price to Cash Flow)
- D/E (Debt to Equity)
- Pretax Profit Margin

## Code Separation Implementation

### Problem Statement

The original monolithic implementation had the following issues:

1. Downloading occurred during visualization (slow user experience)
2. Mixed responsibilities (data acquisition + presentation)
3. Difficult to test individual components
4. Unpredictable performance

### Solution Architecture

#### Before (Monolithic)
```
visualizer.py
├── set_identity() (executed on import)
├── update_company_list() (executed on import)
└── generate_graph()
    └── SecTools_export_important_data() (downloads during visualization)
```

#### After (Separated)
```
downloader.py (CLI)                visualizer.py (Web)
├── setup_sec_identity()          └── generate_graph()
├── update_companies()                 └── _read_json() (local files only)
└── download_all_companies()
    └── SecTools_export_important_data()
        └── save_financials_as_json()
            └── xbrl_data_json/*.json -----> (input for visualizer)
```

### Implementation Changes

#### 1. Code Relocation

**Functions moved from `info_picker_2.py` to `downloader.py`:**
- `set_identity()` call
- `update_company_list()` call

**Code removed from `visualizer.py`:**
- Automatic download loop checking for insufficient data
- Call to `SecTools_export_important_data()` during graph generation
- File reloading after download

#### 2. Modified Logic in visualizer.py

**Original code (lines 232-254):**
```python
# Removed: Automatic download if insufficient data
for year in range(start_year, end_year + 1):
    if sum(1 for d, _ in filings_loaded if d.year == year) < 4:
        updated_company = info_picker_2.SecTools_export_important_data(
            company, companies, year, mapping_variables=MAPPING_VARIABLE
        )
        # ... reload files
```

**New code:**
```python
# Read local files only
if os.path.exists(json_dir):
    for file in os.listdir(json_dir):
        if file.endswith(".json") and company.ticker in file:
            filepath = os.path.join(json_dir, file)
            data = _read_json(filepath)
            if not data:
                continue
            dt = pd.to_datetime(data.get("date")).normalize()
            if start_year <= dt.year <= end_year:
                filings_loaded.append((dt, data))
else:
    print(f"[WARNING] No local data for {company.ticker}. Run 'python downloader.py' first.")
    continue
```

#### 3. Modified Logic in info_picker_2.py

**Original (lines 910-911):**
```python
set_identity("Tomas Carvalho tomasdfc@mac.com")
update_company_list()
```

**New (commented out):**
```python
# NOTE: Identity configuration and company list updates
# have been moved to downloader.py
# 
# For manual configuration, use:
# set_identity("Your Name your.email@example.com")
# update_company_list()
```

#### 4. Bug Fix in downloader.py

**Issue:** `RuntimeError: dictionary changed size during iteration`

**Original code (line 171):**
```python
for idx, (cik, company) in enumerate(companies_data.companies.items(), 1):
```

**Fixed code:**
```python
for idx, (cik, company) in enumerate(list(companies_data.companies.items()), 1):
```

**Explanation:** The `list()` wrapper creates a static snapshot of dictionary items, preventing errors when the dictionary is modified within the loop by `SecTools_export_important_data()`.

## Workflow

### Standard Workflow

1. **Initial Setup**
   ```bash
   pip install -r requirements.txt
   ```

2. **Data Acquisition** (execute once or when updates needed)
   ```bash
   python downloader.py --years 2022 2023 2024 --limit 50
   ```

3. **Data Visualization** (execute anytime, instant startup)
   ```bash
   python visualizer.py
   # Navigate to http://127.0.0.1:8050/
   ```

### Performance Characteristics

| Operation | Before | After |
|-----------|--------|-------|
| Visualizer startup | 30-60 seconds | ~1 second |
| Graph generation | 5-10 seconds | ~0.5 seconds |
| Download time | N/A | 3-5 seconds per company |
| Testing cycle | Slow | Fast |

### Data Flow

```
SEC API
  |
  v
downloader.py (via edgartools/requests)
  |
  v
XBRL Parser (edgartools.Financials)
  |
  v
indicators.py (compute_ratios)
  |
  v
xbrl_data_json/{TICKER}/{TICKER}_{DATE}.json
  |
  v
visualizer.py (_read_json)
  |
  v
Plotly Graph (browser)
```

## Testing

### Automated Test Suite (test_separation.py)

The test suite validates the separation implementation:

1. **Import Test**: Verifies all modules can be imported
2. **File Structure Test**: Checks existence of required files
3. **Function Test**: Validates downloader functions exist
4. **Modification Test**: Confirms visualizer no longer contains download logic
5. **Data Directory Test**: Checks for data availability

**Execution:**
```bash
python test_separation.py
```

**Expected Output:**
```
RESULT: 5/5 tests passed (after pip install -r requirements.txt)
```

## Dependencies

### Production Dependencies

```
pandas==2.2.0              # Data manipulation
numpy==1.26.4              # Numerical computations
requests==2.31.0           # HTTP client
beautifulsoup4==4.12.3     # HTML parsing
lxml==5.1.0                # XML/HTML parser
yfinance==0.2.48           # Yahoo Finance API
edgartools==2.34.2         # SEC EDGAR API
dash==2.18.2               # Web framework
dash-bootstrap-components==1.6.0  # UI components
plotly==5.24.1             # Graphing library
Flask==3.0.3               # WSGI framework
Werkzeug==3.0.4            # WSGI utilities
```

### Installation

```bash
pip install -r requirements.txt
```

## File Structure

```
OP-screener/
├── downloader.py              # CLI download tool (new)
├── visualizer.py              # Web dashboard (modified)
├── info_picker_2.py           # SEC API integration
├── helper.py                  # Utility functions
├── indicators.py              # Ratio calculations
├── requirements.txt           # Python dependencies
├── company_tickers.json       # Company list (generated)
├── test_separation.py         # Test suite
├── TECHNICAL_DOCUMENTATION.md # This file
├── LICENSE                    # License information
├── xbrl_data_json/            # Downloaded data (generated)
│   ├── AAPL/
│   │   └── AAPL_*.json
│   ├── MSFT/
│   └── ...
└── venv/                      # Virtual environment (excluded from git)
```

## Configuration

### SEC API Access

The downloader requires SEC API authentication:

```python
# In downloader.py
set_identity("Your Name your.email@example.com")
```

SEC rate limits: ~10 requests/second

### Yahoo Finance Integration

Optional stock price integration via yfinance:
- Used for P/E, P/FCF, P/CF ratio calculations
- Fallback to filing data if unavailable
- Configurable via checkbox in visualizer interface

## Performance Considerations

### Download Performance

- **Estimated time for 500 companies, 10 years**: 15-20 hours
- **Rate limiting**: SEC API throttles requests
- **Recommendation**: Use `--limit` for testing, run full downloads overnight

### Memory Usage

- **JSON file size**: ~20-50 KB per filing
- **Total storage for 500 companies x 10 years**: ~2 GB
- **Runtime memory**: ~200-500 MB for visualizer

### Optimization Strategies

1. **Incremental downloads**: Downloader skips existing files
2. **Local caching**: Index lists cached for 24 hours
3. **Lazy loading**: Visualizer loads only selected company data
4. **JSON format**: More compact than raw XBRL

## Error Handling

### Common Issues

**1. Missing company_tickers.json**
- Cause: Initial download not executed
- Solution: Run `python downloader.py` (creates file automatically)

**2. Empty visualizer graphs**
- Cause: No data downloaded for selected companies
- Solution: Run `python downloader.py --limit 10` first

**3. Wikipedia 403 errors**
- Cause: Index scraping blocked by Wikipedia
- Solution: Cached data used if available; otherwise index features unavailable

**4. SEC API rate limiting**
- Cause: Too many requests
- Solution: Implemented automatic delays; use `--limit` for testing

## Development Guidelines

### Adding New Financial Indicators

1. Add XBRL concept tags to `_REQUIRED_FOR_COMPUTED` in `indicators.py`
2. Create calculation function (e.g., `calculate_NEW_RATIO()`)
3. Add to `compute_ratios()` function
4. Update `RATIO_VARIABLES` list in `visualizer.py`
5. Update UI dropdown options

### Adding New Data Sources

1. Implement fetcher function in `info_picker_2.py`
2. Add to `save_financials_as_json()` workflow
3. Update JSON schema documentation
4. Modify visualizer graph generation if needed

### Testing Workflow

1. Modify code
2. Run `python test_separation.py`
3. Test with `python downloader.py --limit 3 --years 2024`
4. Verify data in `xbrl_data_json/`
5. Test visualization with `python visualizer.py`

## Project Benefits

### Technical Improvements

1. **Separation of Concerns**: Download and visualization are independent
2. **Performance**: Visualizer starts instantly with local data
3. **Testability**: Each module can be tested independently
4. **Maintainability**: Clear responsibilities and interfaces
5. **Scalability**: Can download data in batches, visualize incrementally

### Educational Value

This project demonstrates software engineering best practices:
- Single Responsibility Principle (SRP)
- Command-line interface design
- Web application architecture
- Financial data processing
- API integration
- Error handling
- Testing strategies

## License

See LICENSE file for licensing information.

## Contact

**Developer**: Tomas de Freitas Carvalho  
**Email**: tomasdfc@mac.com  
**Date**: January 2026  
**Project**: OP-Screener (Downloader/Visualizer Separation)

---

**End of Technical Documentation**
