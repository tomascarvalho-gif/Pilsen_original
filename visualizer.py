"""
Visualizer.py - Interface de visualização de dados financeiros

Este script cria uma aplicação web interativa usando Dash para visualizar
dados financeiros previamente baixados.

IMPORTANTE: Este script apenas VISUALIZA dados locais.
Para baixar novos dados, execute primeiro: python downloader.py

Uso:
    python visualizer.py

Acesse: http://127.0.0.1:8050/
"""

import os
import json
import sys
from datetime import datetime
from typing import List, Optional, Dict
import dash_bootstrap_components as dbc

import dash
import pandas as pd
from dash import dcc, html, dash_table, callback_context, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

import info_picker_2
from helper import human_format, extract_selected_indexes
import numpy as np # Added for correlation

# ----------------------------- CONSTANTS -----------------------------------
# Translation dictionary
# GAAP/base variables only (mapped to us-gaap codes)
MAPPING_VARIABLE: Dict[str, str] = {
    "Total assets": "us-gaap_Assets",
    "Total liabilities": "us-gaap_Liabilities",
    "Cash": "us-gaap_CashAndCashEquivalentsAtCarryingValue",
    "Net income": "us-gaap_NetIncomeLoss",
    "Total shareholders’ equity": "us-gaap_StockholdersEquity",
    "Shares diluted": "us-gaap_EarningsPerShareDiluted",
    "Shares basic": "us-gaap_EarningsPerShareBasic",
    # Q4: AI / R&D investment proxies
    "R&D Expense": "us-gaap_ResearchAndDevelopmentExpense",
    "CAPEX": "us-gaap_PaymentsToAcquirePropertyPlantAndEquipment",
    # For market-cap weighting
    "Shares outstanding": "us-gaap_CommonStockSharesOutstanding",
}

# Computed-only variables (never stored in 'base', only in 'computed')
RATIO_VARIABLES: List[str] = [
    "ROE",
    "ROA",
    "P/E",
    "P/FCF",
    "P/CF",
    "D/E",
    "Pretax Profit Margin"
]

# Special variables (neither GAAP nor ratio) read directly from JSON
SPECIAL_VARIABLES: List[str] = [
    "Stock value",  # reads json["yf_value"]
]

# Combined for UI dropdowns
VARIABLES: List[str] = list(MAPPING_VARIABLE.keys()) + RATIO_VARIABLES + SPECIAL_VARIABLES

YEAR_RANGE = {"start": 2000, "end": 2025}

# Translation dictionary
TRANSLATIONS = {
    "cs": {  # Czech
        "title": "Interaktivní vizualizace filingů",
        "select_company": "Vyberte společnost, index nebo sektor:",
        "select_company_placeholder": "Vyberte jednu či více společností, index nebo sektor",
        "select_variables_graph": "Vyberte proměnné (graf):",
        "select_variables_placeholder": "Vyberte jednu nebo více proměnných",
        "year_range": "Rozsah let:",
        "from_year": "Od roku",
        "to_year": "Do roku",
        "include_yahoo": "Zahrnout data z Yahoo",
        "update_period": "Aktualizuj období",
        "indicators_table": "Tabulka ukazatelů",
        "select_variables_table": "Vyberte proměnné (tabulka):",
        "select_variables_table_placeholder": "Vyberte jednu či více proměnných pro tabulku",
        "update_table": "Aktualizuj tabulku",
        "graph_title": "Vývoj vybraných proměnných",
        "xaxis_title": "Datum filingů",
        "yaxis_title": "Hodnota (filings)",
        "yaxis2_title": "Index (Yahoo)",
        "error_select_company": "Vyberte alespoň jednu společnost nebo index.",
        "error_valid_years": "Zadejte platné roky (např. 2018 až 2022).",
        "error_year_range": "Počáteční rok musí být menší nebo roven koncovému roku.",
        "empty_graph_title": "Vyberte alespoň jednu společnost nebo index.",
        "empty_graph_xaxis": "Datum",
        "empty_graph_yaxis": "Hodnota",
        "language_button": "English"
    },
    "en": {  # English
        "title": "Interactive Filing Visualization",
        "select_company": "Select company / index / sector:",
        "select_company_placeholder": "Select companies, index or sector",
        "select_variables_graph": "Select variables (graph):",
        "select_variables_placeholder": "Select one or more variables",
        "year_range": "Year range:",
        "from_year": "From year",
        "to_year": "To year",
        "include_yahoo": "Include Yahoo data",
        "update_period": "Update period",
        "indicators_table": "Indicators Table",
        "select_variables_table": "Select variables (table):",
        "select_variables_table_placeholder": "Select one or more variables for table",
        "update_table": "Update table",
        "graph_title": "Development of Selected Variables",
        "xaxis_title": "Filing Date",
        "yaxis_title": "Value (filings)",
        "yaxis2_title": "Index (Yahoo)",
        "error_select_company": "Select at least one company or index.",
        "error_valid_years": "Enter valid years (e.g. 2018 to 2022).",
        "error_year_range": "Start year must be less than or equal to end year.",
        "empty_graph_title": "Select at least one company or index.",
        "empty_graph_xaxis": "Date",
        "empty_graph_yaxis": "Value",
        "language_button": "Česky"
    }
}

# ... (skip to PRESET_SOURCES)

# Current language state (stored in dcc.Store)
DEFAULT_LANGUAGE = "cs"

# Load S&P 1500 (500 + 400 + 600) Sector Data
sp1500_data = info_picker_2.download_SP1500_data()

# Parse unique sectors and sub-industries
unique_sectors = set()
unique_sub_industries = set()

for ticker, info in sp1500_data.items():
    if isinstance(info, dict):
        unique_sectors.add(info.get("sector", "Unknown"))
        if info.get("sub_industry", "Unknown") != "Unknown":
            unique_sub_industries.add(info.get("sub_industry"))
    else:
        unique_sectors.add(info)

unique_sectors = sorted(list(unique_sectors))
unique_sub_industries = sorted(list(unique_sub_industries))

PRESET_SOURCES = {
    "sp500": {
        "label": "S&P 500",
        "loader": info_picker_2.download_SP500_tickers,
        "shortcut": "^SPX"  
    },
    "dowjones": {
        "label": "Dow Jones Industrial Average",
        "loader": info_picker_2.download_DJI_tickers,
        "shortcut": "^DJI"
    }
}

def _loader_sector(s):
    return [t for t, info in sp1500_data.items() if (info.get("sector") if isinstance(info, dict) else info) == s]

# Add Sectors to Presets
for sector in unique_sectors:
    slug = f"SECTOR_{sector.replace(' ', '_').upper()}"
    PRESET_SOURCES[slug] = {
        "label": f"Sector: {sector}",
        "loader": __import__("functools").partial(_loader_sector, sector),
        "shortcut": slug,
        "is_sector": True,
        "sector_name": sector
    }

def _loader_sub(s):
    return [t for t, info in sp1500_data.items() if isinstance(info, dict) and info.get("sub_industry") == s]

# Add Sub-Industries to Presets
for sub in unique_sub_industries:
    slug = f"SUBIND_{sub.replace(' ', '_').upper()}"
    PRESET_SOURCES[slug] = {
        "label": f"Sub-Industry: {sub}",
        "loader": __import__("functools").partial(_loader_sub, sub),
        "shortcut": slug,
        "is_sector": True,
        "sector_name": sub
    }

# ----------------------------- LOAD COMPANY DATA ---------------------------
companies = info_picker_2.CompanyData()
companies.load_saved_companies()
TICKER_TO_CIK = {v.ticker.upper(): k for k, v in companies.companies.items()}


# ----------------------------- HELPERS -------------------------------------
def get_text(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """Get translated text for a given key."""
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)

def _to_sheet(sheet_like):
    """Wrap any input so that `.data` is a DataFrame."""
    if sheet_like is None:
        df = pd.DataFrame()
    elif isinstance(sheet_like, pd.DataFrame):
        df = sheet_like
    elif isinstance(sheet_like, dict):
        df = pd.DataFrame.from_dict(sheet_like)
    elif hasattr(sheet_like, "data"):
        raw = getattr(sheet_like, "data")
        if isinstance(raw, pd.DataFrame):
            df = raw
        elif isinstance(raw, dict):
            df = pd.DataFrame.from_dict(raw)
        else:
            try:
                df = pd.DataFrame(raw)
            except Exception:
                df = pd.DataFrame()
    else:
        try:
            df = pd.DataFrame(sheet_like)
        except Exception:
            df = pd.DataFrame()
    return type("Sheet", (object,), {"data": df})()


def build_table_variable_options():
    """Options for the summary table variable picker (base + ratios + specials)."""
    final = list(MAPPING_VARIABLE.keys()) + RATIO_VARIABLES + SPECIAL_VARIABLES
    return [{"label": v, "value": v} for v in final]


def _read_json(filepath: str) -> Optional[dict]:
    try:
        # Check if file is completely empty to avoid JSONDecodeError spam
        if os.path.getsize(filepath) == 0:
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Failed to read (corrupt JSON, etc). Silent fail instead of terminal flooding.
        return None


def extract_from_base_or_computed(json_dict: dict, human_variable: str) -> Optional[float]:
    """
    Read a variable from JSON 'base'/'computed' or (for specials) from top-level JSON.
    - GAAP variables: read base[us-gaap_*] using MAPPING_VARIABLE.
    - Ratios (ROE, P/E): read from computed[<ratio>].
    - Special "Stock value": read json["yf_value"].
    """
    if not isinstance(json_dict, dict):
        return None
    base = json_dict.get("base", {}) or {}
    computed = json_dict.get("computed", {}) or {}

    # Ratios → computed only
    if human_variable in RATIO_VARIABLES:
        val = computed.get(human_variable)
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    # Specials
    if human_variable == "Stock value":
        try:
            val = json_dict.get("yf_value")
            return float(val) if val is not None else None
        except Exception:
            return None

    # GAAP variables → base via code
    code = MAPPING_VARIABLE.get(human_variable)
    if code and code in base:
        try:
            return float(base[code])
        except Exception:
            return None

    return None


# ----------------------------- SUMMARY TABLE --------------------------------
def load_summary_table(selected_variables=None, selected_ciks=None, selected_indexes=None, year_range=None, use_yahoo=False):
    if not selected_variables:
        vars_to_use = list(VARIABLES)
    else:
        vars_to_use = [v for v in selected_variables if (
            v in MAPPING_VARIABLE or v in RATIO_VARIABLES or v in SPECIAL_VARIABLES
        )]
        if not vars_to_use:
            vars_to_use = list(VARIABLES)

    # 1. Resolve selected CIKs from presets (Sectors/Sub-Industries)
    valid_ciks = set()
    if selected_ciks:
        for cik in selected_ciks:
            preset = PRESET_SOURCES.get(cik)
            if preset and preset.get("loader"):
                tickers = preset["loader"]()
                for t in tickers:
                    if t.upper() in TICKER_TO_CIK:
                        valid_ciks.add(TICKER_TO_CIK[t.upper()])
            else:
                valid_ciks.add(cik)
    
    # If explicitly filtered but nothing found, return empty early
    if selected_ciks and not valid_ciks:
        return pd.DataFrame()

    # 2. Extract Index data if requested and Yahoo is enabled
    index_series = {}
    if use_yahoo and selected_indexes:
        indexes = extract_selected_indexes(selected_indexes)
        if not indexes and selected_indexes:
            indexes = [selected_indexes[0]]
        for idx in indexes:
            dates, vals = info_picker_2.yf_download_series_xy(idx, year_range[0] if year_range else 2000, year_range[1] if year_range else 2025)
            if dates and vals:
                index_series[idx] = pd.Series(vals, index=pd.to_datetime(dates)).sort_index()

    records = []
    for cik, company in companies.companies.items():
        if valid_ciks and cik not in valid_ciks:
            continue
            
        ticker, name = company.ticker, company.title
        json_dir = f"xbrl_data_json/{ticker}"
        if not os.path.exists(json_dir):
            continue

        for file in os.listdir(json_dir):
            if not file.endswith(".json"):
                continue
            filepath = os.path.join(json_dir, file)
            data = _read_json(filepath)
            if not data:
                continue
            report_date = pd.to_datetime(data.get("date", None))
            if not report_date:
                continue
            
            # Filter by Year Range
            if year_range and (report_date.year < year_range[0] or report_date.year > year_range[1]):
                continue

            row = {"CIK": cik, "Ticker": ticker, "Company": name, "Date": report_date.strftime("%Y-%m-%d")}
            for var in vars_to_use:
                val = extract_from_base_or_computed(data, var)
                try:
                    if val is not None:
                        f_val = float(val)
                        row[var] = int(f_val) if f_val.is_integer() else f_val
                    else:
                        row[var] = None
                except Exception:
                    row[var] = val
            
            # Add Index Value to the row if it exists
            for idx_name, series in index_series.items():
                col_name = f"Index: {idx_name}"
                if col_name not in vars_to_use:
                    vars_to_use.append(col_name) # Ensure it gets picked up
                try:
                    # Get nearest previous value
                    nearest_idx = series.index.get_indexer([report_date], method='pad')[0]
                    if nearest_idx != -1:
                        row[col_name] = round(series.iloc[nearest_idx], 2)
                    else:
                        row[col_name] = None
                except Exception:
                    row[col_name] = None

            records.append(row)

    columns = ["CIK", "Ticker", "Company", "Date"] + vars_to_use
    # Remove duplicates from columns just in case
    columns = list(dict.fromkeys(columns))
    df = pd.DataFrame(records, columns=columns)
    if not df.empty:
        df.sort_values(["Company", "Date"], inplace=True)
    return df


# ----------------------------- GRAPH GENERATION -----------------------------
def generate_graph(selected_ciks, selected_variables, selected_indexes, start_year, end_year, use_yahoo, language=DEFAULT_LANGUAGE, set_progress=None, log_func=None):
    if log_func is None:
        log_func = print
    fig = go.Figure()

    if not selected_ciks and not selected_indexes:
        fig.update_layout(
            title=get_text("empty_graph_title", language),
            xaxis_title=get_text("empty_graph_xaxis", language),
            yaxis_title=get_text("empty_graph_yaxis", language)
        )
        return fig

    if not selected_variables:
        selected_variables = ["Total assets"]
        log_func("[INFO] Default variable: Total assets")

    current_year = datetime.now().year
    start_year, end_year = min(start_year, end_year), max(start_year, end_year)
    if start_year > current_year or end_year > current_year:
        log_func(f"[ERROR] Year out of range. Current year: {current_year}")
        return fig

    # --- company filings (primary axis) ---
    # --- company filings (primary axis) ---
    ciks_list = selected_ciks or []
    total_ciks = len(ciks_list)
    
    for idx, cik in enumerate(ciks_list):
        if set_progress:
            pct = int((idx / max(1, total_ciks)) * 100)
            msg_cz = f"Vykreslování grafu... ({idx+1}/{total_ciks} - {pct}%)"
            msg_en = f"Drawing graph... ({idx+1}/{total_ciks} - {pct}%)"
            set_progress(f"{msg_cz} / {msg_en}")

        # HANDLE SECTORS
        if str(cik).startswith(("SECTOR_", "SUBIND_")):
            preset = PRESET_SOURCES.get(cik)
            label = preset["label"] if preset else cik
            log_func(f"Zpracování sektoru / Processing sector aggregation: {label}...")
            
            sector_dates, sector_vals = calculate_sector_stats(cik, start_year, end_year)
            if sector_dates and sector_vals:
                fig.add_trace(go.Scatter(
                    x=sector_dates,
                    y=sector_vals,
                    mode='lines',
                    name=label,
                    hovertemplate=f"{label}<br>Date: %{{x|%Y-%m-%d}}<br>Index: %{{y:.2f}}<extra></extra>"
                ))
            continue

        company = companies.companies.get(cik)
        if not company:
            continue

        log_func(f"Načítání / Loading local XBRL data for: {company.title} ({company.ticker})...")
        
        json_dir = f"xbrl_data_json/{company.ticker}"
        filings_loaded = []
        
        # MODIFICADO: Apenas ler arquivos JSON locais, sem download automático
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
            print(f"[WARNING] Sem dados locais para {company.ticker}. Execute 'python downloader.py' primeiro.")
            continue
        
        if not filings_loaded:
            print(f"[WARNING] Nenhum dado encontrado para {company.ticker} no período {start_year}-{end_year}.")

        for human_var in selected_variables:
            xs, ys, customdata = [], [], []

            is_ratio = human_var in RATIO_VARIABLES
            is_special_stock = (human_var == "Stock value")
            code = MAPPING_VARIABLE.get(human_var, human_var)

            for filing_dt, json_data in filings_loaded:
                if is_ratio:
                    # Read from computed
                    comp = (json_data.get("computed") or {})
                    value = comp.get(human_var)
                elif is_special_stock:
                    # Read saved Yahoo price directly from JSON
                    value = json_data.get("yf_value")
                else:
                    # GAAP variable: use helper to extract from base sheets
                    try:
                        value = info_picker_2.get_file_variable(code, json_data, year=filing_dt.year)
                    except Exception as e:
                        print(f"[ERROR] get_file_variable({code}) failed for {company.ticker}: {e}")
                        value = None

                y_num = None
                try:
                    y_num = float(value) if value is not None else None
                except Exception:
                    pass

                xs.append(filing_dt)
                ys.append(y_num)

                pretty_val = None
                if y_num is not None:
                    if is_ratio:
                        pretty_val = f"{y_num:.2f}"
                    elif is_special_stock:
                        pretty_val = f"{y_num:.2f} $"
                    else:
                        pretty_val = human_format(y_num)
                row = [pretty_val]
                customdata.append(row)

            # sort & filter out None
            combined = [(d, v, cd) for d, v, cd in zip(xs, ys, customdata) if v is not None]
            combined.sort(key=lambda x: x[0])
            if not combined:
                continue
            x_sorted, y_sorted, cd_sorted = zip(*combined)

            tooltip = (
                f"{company.title} - {human_var}<br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Value: %{customdata[0]}<br>"
            )

            # Attach Yahoo price per filing date (skip duplication if we're already plotting Stock value)
            if use_yahoo and human_var != "Stock value":
                yf_map = info_picker_2.yf_get_stock_data(company.ticker, start_year, end_year) or {}
                yf_by_date = {pd.to_datetime(d).date(): v for d, v in yf_map.items() if v is not None}

                new_cd, has_any = [], False
                for d, row in zip(x_sorted, cd_sorted):
                    v = yf_by_date.get(d.date())
                    row = list(row)
                    row.append(v if v is not None else None)
                    if v is not None:
                        has_any = True
                    new_cd.append(row)
                cd_sorted = tuple(new_cd)
                if has_any:
                    tooltip += "Yahoo close: %{customdata[1]:.2f} $<br>"

            tooltip += "<extra></extra>"

            fig.add_trace(go.Scatter(
                x=list(x_sorted),
                y=[float(v) for v in y_sorted],
                mode='lines+markers',
                name=f"{company.title} - {human_var}",
                customdata=list(cd_sorted),
                hovertemplate=tooltip
            ))

    # --- Yahoo index overlay (secondary axis) ---
    if selected_indexes:
        for idx in selected_indexes:
            log_func(f"Stahování tržních dat / Downloading market data: {idx}...")
            xy = info_picker_2.yf_download_series_xy(idx, start_year, end_year)
            if not xy:
                log_func(f"[WARNING] Index series empty for {idx}")
                continue
            x_vals, y_vals = xy
            fig.add_trace(go.Scatter(
                x=list(x_vals),
                y=[float(v) for v in y_vals],
                mode="lines",
                name=f"{idx} (Yahoo)",
                line=dict(dash="dash", width=3),
                yaxis="y2",
                hovertemplate="Index %{fullData.name}<br>Date: %{x|%Y-%m-%d}<br>Close: %{y:.2f} $<extra></extra>"
            ))

    fig.update_layout(
        title=get_text("graph_title", language),
        xaxis_title=get_text("xaxis_title", language),
        yaxis_title=get_text("yaxis_title", language),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="black",  # solid white background
            font_size=14,  # adjust to taste
            font_color="white"  # full color text
        ),
        yaxis=dict(type="log"),
        yaxis2=dict(
            title=get_text("yaxis2_title", language),
            overlaying="y",
            side="right",
            type="linear",
            showgrid=False
        ),
        legend=dict(x=1.10, y=1, xanchor="left", yanchor="top")
    )

    # Highlight COVID impact period
    fig.add_vrect(
        x0="2020-01-01", x1="2021-03-31",
        fillcolor="red", opacity=0.1,
        layer="below", line_width=0,
        annotation_text="COVID", annotation_position="top left"
    )

    fig.update_xaxes(type="date", tickformat="%Y-%m-%d")
    return fig


def filter_summary_table(n_clicks, filter_value):
    if not filter_value or filter_value.strip() == "":
        return summary_df.to_dict("records")
    try:
        filtered_df = summary_df.query(filter_value)
        return filtered_df.to_dict("records")
    except Exception as e:
        print(f"[FILTER ERROR] {e}")
        return summary_df.to_dict("records")


# --------- Dropdown options incl. index shortcuts --------------------------
def build_company_dropdown_options():
    options = []
    options.append({"label": "— Indexes —", "value": "__SEP__IDX__", "disabled": True})
    for key, meta in PRESET_SOURCES.items():
        options.append({"label": meta["label"], "value": meta["shortcut"]})
    options.append({"label": "— All companies —", "value": "__SEP__ALL__", "disabled": True})
    for cik, comp in companies.companies.items():
        options.append({"label": f"{comp.title} [{comp.ticker}] ({cik})", "value": cik})
    return options

def build_variable_dropdown_options():
    """Group dropdown for the graph/table: base (human names), computed, specials."""
    options = []
    options.append({"label": "— Base variables —", "value": "__SEP__BASE__", "disabled": True})
    for key in MAPPING_VARIABLE.keys():
        options.append({"label": key, "value": key})  # value = human label

    options.append({"label": "— Computed variables —", "value": "__SEP__COM__", "disabled": True})
    for key in RATIO_VARIABLES:
        options.append({"label": key, "value": key})

    options.append({"label": "— Special variables —", "value": "__SEP__SPE__", "disabled": True})
    for key in SPECIAL_VARIABLES:
        options.append({"label": key, "value": key})
    return options


def expand_selected_values(values):
    """
    Expand index values (e.g., ^SPX, ^DJI) into constituent CIKs; keep direct CIKs as-is.
    IMPORTANT: If loader fails (e.g., HTTP 403), we return no expansion rather than raising.
    """
    if not values:
        return []
    expanded = set()
    for val in values:
        if isinstance(val, str) and val.startswith("^"):
            preset = next((m for m in PRESET_SOURCES.values() if m.get("shortcut") == val), None)
            if not preset:
                continue
            tickers = []
            try:
                tickers = preset["loader"]() or []
            except Exception as e:
                # Never break the whole flow if Wikipedia blocks scraping
                print(f"[ERROR] loader preset for {val}: {e} (continuing without expansion)")
                tickers = []
            for t in tickers:
                cik = TICKER_TO_CIK.get(str(t).upper())
                if cik:
                    expanded.add(cik)
        else:
            expanded.add(str(val))
    return list(expanded)


# ----------------------------- CUSTOM CARDS GENERATION ---------------------
def generate_price_card(cik, start_year, end_year):
    company = companies.companies.get(cik)
    if not company:
        return html.Div()

    # Reuse yf_download_series_xy for daily data
    xy = info_picker_2.yf_download_series_xy(company.ticker, start_year, end_year)
    
    if not xy:
         # Fallback or empty state
        return dbc.Card(
            dbc.CardBody([
                html.H5("Stock Performance", className="card-title text-white"),
                html.P("No data available from Yahoo Finance.", className="text-muted")
            ]),
            style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
        )

    x_vals, y_vals = xy
    if not x_vals:
        return html.Div()

    # Calc stats
    vals = [v for v in y_vals if v is not None]
    if not vals:
        return html.Div()
    
    min_val = min(vals)
    max_val = max(vals)
    avg_val = sum(vals) / len(vals)
    # Simple volatility (std dev)
    import numpy as np
    volatility = np.std(vals)

    # Color logic
    first = vals[0]
    last = vals[-1]
    color = "#34D399" if last >= first else "#F87171"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, 
        y=y_vals, 
        mode='lines', 
        line=dict(color=color, width=2),
        name='Price',
        hovertemplate="Date: %{x|%Y-%m-%d}<br>Price: $%{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=False, showticklabels=True),
        yaxis=dict(showgrid=True, gridcolor="rgba(75,85,99,0.3)"),
        height=250,
        showlegend=False
    )

    stats_style = {"textAlign": "center", "fontSize": "0.9rem", "color": "#9CA3AF"}
    val_style = {"fontWeight": "bold", "fontSize": "1.1rem", "color": "white"}

    return dbc.Card(
        dbc.CardBody([
            html.H5("Stock Performance", className="card-title text-white", style={"marginBottom": "0px"}),
            html.P(f"Price History ({start_year}-{end_year})", className="text-muted", style={"fontSize": "0.8rem"}),
            dcc.Graph(figure=fig, config={'displayModeBar': True}),
            dbc.Row([
                dbc.Col([html.Div("MIN", style=stats_style), html.Div(f"${min_val:.2f}", style=val_style)]),
                dbc.Col([html.Div("MAX", style=stats_style), html.Div(f"${max_val:.2f}", style=val_style)]),
                dbc.Col([html.Div("AVG", style=stats_style), html.Div(f"${avg_val:.2f}", style=val_style)]),
                dbc.Col([html.Div("VOL", style=stats_style), html.Div(f"{volatility:.2f}", style=val_style)]),
            ], style={"marginTop": "15px"})
        ]),
        style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
    )

def generate_eps_card(cik, start_year, end_year):
    company = companies.companies.get(cik)
    if not company: return html.Div()
    
    # Fetch EPS data from local JSONs
    # us-gaap_EarningsPerShareDiluted
    json_dir = f"xbrl_data_json/{company.ticker}"
    data_points = []
    
    if os.path.exists(json_dir):
        for file in os.listdir(json_dir):
            if file.endswith(".json"):
                data = _read_json(os.path.join(json_dir, file))
                if not data: continue
                # Date
                dt = pd.to_datetime(data.get("date"))
                if not (start_year <= dt.year <= end_year):
                    continue
                # Value
                val = extract_from_base_or_computed(data, "Shares diluted") # Mapped to EarningsPerShareDiluted
                if val is not None:
                    data_points.append((dt, val))
    
    data_points.sort(key=lambda x: x[0])
    
    if not data_points:
         return dbc.Card(
            dbc.CardBody([
                html.H5("Quarterly EPS History", className="card-title text-white"),
                html.P("No EPS data available.", className="text-muted")
            ]),
            style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
        )
    
    dates, values = zip(*data_points)
    latest_eps = values[-1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, mode='markers+lines',
        line=dict(color="#F59E0B", width=2),
        marker=dict(size=6, color="#F59E0B"),
        name='EPS',
        hovertemplate="Date: %{x|%Y-%m-%d}<br>EPS: $%{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=False, showticklabels=True),
        yaxis=dict(showgrid=True, gridcolor="rgba(75,85,99,0.3)"),
        height=200,
        showlegend=False
    )
    
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.H5("Quarterly EPS History", className="text-white", style={"display": "inline-block"}),
                html.Div(f"Latest: ${latest_eps:.2f}", className="float-end text-success" if latest_eps > 0 else "float-end text-danger", style={"fontSize": "1rem", "fontWeight": "bold", "float": "right"})
            ]),
            dcc.Graph(figure=fig, config={'displayModeBar': True})
        ]),
        style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
    )

def generate_pe_card(cik, start_year, end_year):
    company = companies.companies.get(cik)
    if not company: return html.Div()
    
    # Fetch P/E data from computed stats
    json_dir = f"xbrl_data_json/{company.ticker}"
    data_points = []
    
    # Ensure we have price data for P/E calculation
    # This will fetch and save yf_value to JSONs if missing
    info_picker_2.yf_get_stock_data(company.ticker, start_year, end_year)

    if os.path.exists(json_dir):
        for file in os.listdir(json_dir):
            if file.endswith(".json"):
                data = _read_json(os.path.join(json_dir, file))
                if not data: continue
                dt = pd.to_datetime(data.get("date"))
                if not (start_year <= dt.year <= end_year): continue
                
                # Extract P/E
                val = extract_from_base_or_computed(data, "P/E")
                
                # Fallback: Compute P/E if missing
                if val is None:
                    eps = extract_from_base_or_computed(data, "Shares diluted") # EPS
                    # Try to get price from JSON directly (now likely populated)
                    price = data.get("yf_value")
                    
                    if eps and price:
                         try:
                             val = float(price) / float(eps)
                         except ZeroDivisionError:
                             val = None

                if val is not None:
                    data_points.append((dt, val))
    
    data_points.sort(key=lambda x: x[0])
    
    if not data_points:
         return dbc.Card(
            dbc.CardBody([
                html.H5("P/E Ratio History", className="card-title text-white"),
                html.P("No P/E data available (requires price data).", className="text-muted")
            ]),
            style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
        )

    dates, values = zip(*data_points)
    current_pe = values[-1]
    
    # Rating
    rating_color = "#4ADE80" # green
    rating_text = "(Low)"
    if current_pe > 25:
        rating_color = "#FACC15" # yellow
        rating_text = "(High)"
    elif current_pe > 15:
        rating_color = "#60A5FA" # blue
        rating_text = "(Average)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, mode='lines+markers',
        line=dict(color="#2563EB", width=2),
        marker=dict(size=4, color="#2563EB"),
        name='P/E',
        hovertemplate="Date: %{x|%Y-%m-%d}<br>P/E: %{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=False, showticklabels=True),
        yaxis=dict(showgrid=True, gridcolor="rgba(75,85,99,0.3)"),
        height=200,
        showlegend=False
    )
    
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.H5("P/E Ratio History", className="text-white", style={"display": "inline-block"}),
                html.Div([
                    html.Span(f"{current_pe:.1f} ", style={"fontSize": "1.1rem", "fontWeight": "bold", "color": "white"}),
                    html.Span(rating_text, style={"color": rating_color, "fontSize": "0.9rem"})
                ], style={"float": "right"})
            ]),
            dcc.Graph(figure=fig, config={'displayModeBar': True})
        ]),
        style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
    )


def generate_rd_capex_card(cik, start_year, end_year):
    """Q4: R&D + CAPEX investment vs. stock price return card for single company view."""
    company = companies.companies.get(cik)
    if not company:
        return html.Div()

    df = calculate_rd_capex_vs_price(cik, start_year, end_year)

    if df.empty:
        return dbc.Card(
            dbc.CardBody([
                html.H5("R&D + CAPEX vs. Stock Return (Q4)", className="card-title text-white"),
                html.P("No R&D or CAPEX data available in filings.", className="text-muted")
            ]),
            style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
        )

    corr = df["RD_CAPEX_Growth"].corr(df["Price_Growth"])
    corr_str = f"{corr:.2f}" if not pd.isna(corr) else "N/A"

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df["RD_CAPEX_Growth"],
        name="R&D+CAPEX Growth (YoY %)",
        marker_color="#6EE7B7",
        opacity=0.75,
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Price_Growth"],
        name="Stock Price Return (YoY %)",
        mode="lines+markers",
        line=dict(color="#F59E0B", width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        title=f"R&D+CAPEX vs. Stock Return (r={corr_str})",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=250,
        yaxis=dict(title="R&D+CAPEX Growth %"),
        yaxis2=dict(title="Price Return %", overlaying="y", side="right", showgrid=False),
        legend=dict(x=0, y=1.15, orientation="h"),
        margin=dict(l=40, r=40, t=80, b=10),
        barmode="group"
    )

    return dbc.Card(
        dbc.CardBody([
            dcc.Graph(figure=fig, config={"displayModeBar": True})
        ]),
        style={"backgroundColor": "#1f2937", "borderColor": "#374151", "marginBottom": "20px"}
    )


# ----------------------------- ANALYTICAL HELPERS ---------------------------
def calculate_sector_stats(sector_slug, start_year, end_year):
    """
    Compute sector index performance. 
    Ideally market-cap weighted, but for MVP we use equal-weight average of normalized prices.
    Returns: (dates, values)
    """
    preset = PRESET_SOURCES.get(sector_slug)
    if not preset: return None, None
    
    tickers = preset["loader"]()
    if not tickers: return None, None

    # Collect all series
    all_series = []
    
    # We need a common date range index
    start_date = pd.Timestamp(year=start_year, month=1, day=1)
    end_date = pd.Timestamp(year=end_year, month=12, day=31)
    
    # Use SPX trading days as baseline if possible, else just range
    idx_dates = pd.date_range(start_date, end_date, freq="B") # Business days
    
    df_sector = pd.DataFrame(index=idx_dates)
    
    count = 0
    for tick in tickers:
        # We try to get data from info_picker_2 (cached or fetch)
        # using a specialized fetcher that doesn't print too much
        # For MVP we re-use yf_download_series_xy but suppress output if possible or accept it
        try:
             # Check if we have local cache to speed up? 
             # For now, rely on yfinance caching
             res = info_picker_2.yf_download_series_xy(tick, start_year, end_year)
             if res:
                 ds, vs = res
                 # Create series, reindex to common index
                 s = pd.Series(vs, index=ds)
                 s = s[~s.index.duplicated(keep='first')]
                 
                 # Normalize to start = 100 for equal weighting aggregation
                 if not s.empty:
                     first_val = s.iloc[0]
                     if first_val > 0:
                         s_norm = (s / first_val) * 100
                         df_sector[tick] = s_norm
                         count += 1
        except Exception:
            pass
            
    if count == 0:
        return None, None
        
    # Average across all columns (equal weight sector index)
    sector_index = df_sector.mean(axis=1, skipna=True)
    sector_index = sector_index.dropna()
    
    return sector_index.index.tolist(), sector_index.values.tolist()


def calculate_correlation(series_a_x, series_a_y, series_b_x, series_b_y, window=30):
    """
    Align two series by date and calculate rolling correlation.
    Returns: (dates, correlations)
    """
    s1 = pd.Series(series_a_y, index=series_a_x)
    s2 = pd.Series(series_b_y, index=series_b_x)
    
    # Align
    df = pd.DataFrame({'a': s1, 'b': s2}).dropna()
    
    if df.empty: return [], []
    
    # Rolling correlation
    rolling_corr = df['a'].rolling(window=window).corr(df['b'])
    
    # Remove NaNs
    valid = rolling_corr.dropna()
    return valid.index.tolist(), valid.values.tolist()


def calculate_decline_share(sector_slug, start_year, end_year):
    """
    Calculate % of companies in sector that declined (negative return)
    broken down by Quarter or Year.
    For this MVP: By Year.
    """
    preset = PRESET_SOURCES.get(sector_slug)
    if not preset: return [], []
    tickers = preset["loader"]()
    
    years = range(start_year, end_year + 1)
    decline_rates = []
    
    for y in years:
        start_d = pd.Timestamp(year=y, month=1, day=1)
        end_d = pd.Timestamp(year=y, month=12, day=31)
        
        declined = 0
        total = 0
        
        for tick in tickers:
             # Fast check: get first and last price of year
             # We can use yf_download_price logic or just fetch year
             try:
                 # Fetch just this year
                 res = info_picker_2.yf_download_series_xy(tick, y, y)
                 if res:
                     ds, vs = res
                     if len(vs) > 1:
                         if vs[-1] < vs[0]:
                             declined += 1
                         total += 1
             except: pass
        
        rate = (declined / total * 100) if total > 0 else 0
        decline_rates.append(rate)

    return list(years), decline_rates


def calculate_marketcap_weighted_decline_share(sector_slug, start_year, end_year):
    """
    Market-cap weighted version of decline share.
    Weight of each company = shares_outstanding * stock_price at start of each year.
    Returns: (years, equal_weight_rates, mcap_weight_rates)
    """
    preset = PRESET_SOURCES.get(sector_slug)
    if not preset:
        return [], [], []
    tickers = preset["loader"]()

    years = range(start_year, end_year + 1)
    equal_rates = []
    mcap_rates = []
    
    # --- HOTFIX: Pre-cache shares outstanding and stock prices ---
    ticker_shares_cache = {}
    ticker_price_cache = {}
    for tick in tickers:
        cik = TICKER_TO_CIK.get(tick)
        if not cik: continue
        company = companies.companies.get(cik)
        if not company: continue
        
        # 1. Cache Shares
        json_dir = f"xbrl_data_json/{company.ticker}"
        shares_history = []
        if os.path.exists(json_dir):
            for f in os.listdir(json_dir):
                if not f.endswith(".json"): continue
                data = _read_json(os.path.join(json_dir, f))
                if not data: continue
                dt = pd.to_datetime(data.get("date", ""), errors="coerce")
                if pd.isnull(dt): continue
                s = extract_from_base_or_computed(data, "Shares outstanding")
                if s is not None:
                    shares_history.append((dt, s))
            if shares_history:
                shares_history.sort(key=lambda x: x[0])
        ticker_shares_cache[tick] = shares_history

        # 2. Cache Prices (Single network request per ticker for the entire date range!)
        try:
            res = info_picker_2.yf_download_series_xy(tick, start_year, end_year)
            if res:
                ds, vs = res
                ticker_price_cache[tick] = pd.Series(vs, index=ds)
        except Exception:
            pass
    # -----------------------------------------------------------

    for y in years:
        declined_count = 0
        total_count = 0
        declined_weight = 0.0
        total_weight = 0.0

        for tick in tickers:
            try:
                # Fast lookup from price cache
                price_series = ticker_price_cache.get(tick)
                if price_series is None or price_series.empty:
                    continue
                
                # Filter series to just year y
                y_series = price_series[str(y)]
                if len(y_series) < 2:
                    continue

                declined = y_series.iloc[-1] < y_series.iloc[0]
                start_price = y_series.iloc[0] if y_series.iloc[0] else 1.0

                # Fast lookup from shares cache
                shares = 1.0 # fallback: equal weight
                history = ticker_shares_cache.get(tick, [])
                if history:
                    # Find latest shares where year <= y
                    valid_shares = [s for dt, s in history if dt.year <= y]
                    if valid_shares:
                        shares = valid_shares[-1]

                market_cap = abs(shares) * start_price

                if declined:
                    declined_count += 1
                    declined_weight += market_cap
                total_count += 1
                total_weight += market_cap

            except Exception:
                pass

        equal_rates.append((declined_count / total_count * 100) if total_count > 0 else 0.0)
        mcap_rates.append((declined_weight / total_weight * 100) if total_weight > 0 else 0.0)

    return list(years), equal_rates, mcap_rates


def calculate_cross_sector_correlation(sector_slug_a, sector_slug_b, start_year, end_year, window=60):
    """
    Q3: Rolling correlation between two sector price indexes.
    Returns: (dates, correlations)
    """
    a_dates, a_vals = calculate_sector_stats(sector_slug_a, start_year, end_year)
    b_dates, b_vals = calculate_sector_stats(sector_slug_b, start_year, end_year)
    if not a_dates or not b_dates:
        return [], []
    return calculate_correlation(a_dates, a_vals, b_dates, b_vals, window=window)


def calculate_rd_capex_vs_price(cik, start_year, end_year):
    """
    Q4: For a single company, compute YoY growth of (R&D + CAPEX) vs. stock price return.
    Returns: DataFrame with columns ['RD_CAPEX_Growth', 'Price_Growth'] indexed by Date.
    """
    company = companies.companies.get(cik)
    if not company:
        return pd.DataFrame()

    json_dir = f"xbrl_data_json/{company.ticker}"
    rows = []

    if os.path.exists(json_dir):
        for f in os.listdir(json_dir):
            if not f.endswith(".json"):
                continue
            data = _read_json(os.path.join(json_dir, f))
            if not data:
                continue
            dt = pd.to_datetime(data.get("date", ""), errors="coerce")
            if pd.isnull(dt) or not (start_year <= dt.year <= end_year):
                continue
            rd = extract_from_base_or_computed(data, "R&D Expense")
            if rd is None:
                rd = info_picker_2.get_file_variable("us-gaap_ResearchAndDevelopmentExpense", data, dt.year)
                
            capex = extract_from_base_or_computed(data, "CAPEX")
            if capex is None:
                capex = info_picker_2.get_file_variable("us-gaap_PaymentsToAcquirePropertyPlantAndEquipment", data, dt.year)

            # Convert to float safely, default to 0
            try: rd_float = float(abs(rd)) if rd is not None else 0.0
            except: rd_float = 0.0
            
            try: capex_float = float(abs(capex)) if capex is not None else 0.0
            except: capex_float = 0.0

            total = rd_float + capex_float
            if total > 0:
                rows.append({"Date": dt, "RD_CAPEX": total})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).set_index("Date").sort_index()
    df_q = df.resample("Q").sum()
    df_q["RD_CAPEX_Growth"] = df_q["RD_CAPEX"].pct_change(periods=4) * 100

    # Stock price quarterly returns
    xy = info_picker_2.yf_download_series_xy(company.ticker, start_year, end_year)
    if xy:
        x_dates, y_vals = xy
        price_s = pd.Series(y_vals, index=x_dates)
        price_q = price_s.resample("Q").last()
        df_q["Price_Growth"] = price_q.pct_change(periods=4) * 100

    return df_q[["RD_CAPEX_Growth", "Price_Growth"]].dropna()


def calculate_sector_price_growth(sector_slug, start_year, end_year):
    """
    Calculate Sector Price Growth (YoY or QoQ).
    Returns DataFrame with columns ['Date', 'Growth'].
    """
    dates, values = calculate_sector_stats(sector_slug, start_year, end_year)
    if not dates or not values:
        return pd.DataFrame()

    df = pd.DataFrame({'Date': dates, 'Price': values})
    df.set_index('Date', inplace=True)
    
    # Resample to quarterly to match financial reporting frequency
    df_q = df.resample('Q').last()
    
    # Calculate YoY Growth
    df_q['Growth'] = df_q['Price'].pct_change(periods=4) * 100
    
    return df_q[['Growth']].dropna()


from functools import lru_cache

@lru_cache(maxsize=32)
def calculate_aggregated_indicator_growth(sector_slug, variable, start_year, end_year):
    """
    Aggregate a variable (e.g. Revenue) across all companies in sector 
    and calculate its YoY growth.
    Returns DataFrame with columns ['Date', 'Growth'].
    """
    preset = PRESET_SOURCES.get(sector_slug)
    if not preset: return pd.DataFrame()
    tickers = preset["loader"]()
    
    # We need to aggregate raw values for each quarter
    # This is expensive, so we'll try to be efficient
    
    all_series = []
    
    for tick in tickers:
        cik = TICKER_TO_CIK.get(tick)
        if not cik: continue
        
        company = companies.companies.get(cik)
        if not company: continue

        json_dir = f"xbrl_data_json/{company.ticker}"
        if not os.path.exists(json_dir): continue
        
        # Extract series for this company
        dates = []
        vals = []
        
        for file in os.listdir(json_dir):
            if file.endswith(".json"):
                data = _read_json(os.path.join(json_dir, file))
                if not data: continue
                
                dt = pd.to_datetime(data.get("date")).normalize()
                if start_year <= dt.year <= end_year:
                    val = extract_from_base_or_computed(data, variable)
                    if val is not None:
                        dates.append(dt)
                        vals.append(val)
        
        if dates:
            s = pd.Series(vals, index=dates)
            s = s.sort_index()
            # Resample this company to Calendar Quarters (taking max or sum? usually last reported)
            s_q = s.resample('Q').last() 
            all_series.append(s_q)

    if not all_series:
        return pd.DataFrame()
        
    # Combine all companies into one DataFrame
    df_combined = pd.concat(all_series, axis=1)
    
    # Sum across all companies for each quarter (Aggregated Sector Revenue/NetIncome etc)
    # We use sum for "Total" variables (Revenue, Income, Assets)
    # For Ratios (P/E, ROE), we should probably use Median or Mean
    
    if variable in RATIO_VARIABLES:
        # For ratios, average is better than sum
        agg_series = df_combined.mean(axis=1, skipna=True)
    else:
        # For base vars like Revenue, Assets, sum makes sense for the "Sector Size"
        agg_series = df_combined.sum(axis=1, skipna=True)
        
    # Calculate YoY Growth of the Aggregate
    growth_series = agg_series.pct_change(periods=4) * 100
    
    df_result = pd.DataFrame({'Growth': growth_series})
    return df_result.dropna()


# ----------------------------- APP & CALLBACKS ------------------------------
import diskcache
from dash import DiskcacheManager
cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    background_callback_manager=background_callback_manager
)

# Initial table (Start empty so we don't crash the browser with 50MB of initial JSON data)
summary_columns = [{"name": col, "id": col} for col in ["CIK", "Ticker", "Company", "Date"] + list(VARIABLES)]
summary_data = []

# Language toggle callback
@app.callback(
    Output('language-store', 'data'),
    Input('language-button', 'n_clicks'),
    State('language-store', 'data')
)
def toggle_language(n_clicks, current_language):
    if n_clicks is None or n_clicks == 0:
        return DEFAULT_LANGUAGE
    if current_language == "cs":
        return "en"
    else:
        return "cs"

# Update UI text based on language
@app.callback(
    [Output('main-title', 'children'),
     Output('select-company-label', 'children'),
     Output('company-dropdown', 'placeholder'),
     Output('select-variables-graph-label', 'children'),
     Output('variable-dropdown', 'placeholder'),
     Output('year-range-label', 'children'),
     Output('year-start-input', 'placeholder'),
     Output('year-end-input', 'placeholder'),
     Output('yahoo-checkbox', 'options'),
     Output('draw-button', 'children'),
     Output('indicators-table-title', 'children'),
     Output('select-variables-table-label', 'children'),
     Output('table-variables-dropdown', 'placeholder'),
     Output('update-table-button', 'children'),
     Output('language-button', 'children')],
    Input('language-store', 'data')
)
def update_ui_text(language):
    if not language:
        language = DEFAULT_LANGUAGE
    return (
        get_text("title", language),
        get_text("select_company", language),
        get_text("select_company_placeholder", language),
        get_text("select_variables_graph", language),
        get_text("select_variables_placeholder", language),
        get_text("year_range", language),
        get_text("from_year", language),
        get_text("to_year", language),
        [{'label': get_text("include_yahoo", language), 'value': 'yahoo'}],
        get_text("update_period", language),
        get_text("indicators_table", language),
        get_text("select_variables_table", language),
        get_text("select_variables_table_placeholder", language),
        get_text("update_table", language),
        get_text("language_button", language)
    )

import threading
import time
from contextlib import contextmanager

class ProgressLogCapture:
    def __init__(self, set_progress):
        self.set_progress = set_progress
        self.logs = []
        self.status = ""
        self._lock = threading.Lock()
        self._last_update = 0
        
    def write(self, text):
        if text.strip():
            with self._lock:
                for line in text.strip().split('\n'):
                    if line.strip():
                        self.logs.append(line.strip())
                if len(self.logs) > 6:
                    self.logs = self.logs[-6:]
                sys.__stdout__.write(text)
                sys.__stdout__.flush()
            self._update()
            
    def flush(self):
        sys.__stdout__.flush()
        
    def set_status(self, status):
        with self._lock:
            self.status = status
        self._update(force=True)
        
    def log(self, text):
        with self._lock:
            for line in text.strip().split('\n'):
                if line.strip():
                    self.logs.append(line.strip())
            if len(self.logs) > 6:
                self.logs = self.logs[-6:]
            sys.__stdout__.write(text + "\n")
            sys.__stdout__.flush()
        self._update(force=True)
        
    def _update(self, force=False):
        now = time.time()
        if force or (now - self._last_update > 0.3):
            self.set_progress((self.status, "\n".join(self.logs)))
            self._last_update = now

@contextmanager
def capture_logs_to_progress(set_progress):
    capture = ProgressLogCapture(set_progress)
    try:
        yield capture
    finally:
        pass

@app.callback(
    [Output('filing-graph', 'figure'),
     Output('error-message', 'children'),
     Output('single-company-view', 'children')],
    Input('draw-button', 'n_clicks'),
    [State('company-dropdown', 'value'),
     State('variable-dropdown', 'value'),
     State('year-start-input', 'value'),
     State('year-end-input', 'value'),
     State('filing-graph', 'figure'),
     State('yahoo-checkbox', 'value'),
     State('language-store', 'data')],
    prevent_initial_call=True,
    background=True,
    manager=background_callback_manager,
    running=[
        (Output('draw-button', 'disabled'), True, False)
    ],
    progress=[
        Output('loading-progress', 'children'),
        Output('loading-log', 'children')
    ],
    progress_default=("", "")
)
def unified_callback(set_progress, draw_clicks,
                     selected_values, selected_variables,
                     start_year, end_year, current_fig,
                      yahoo_state, language_data):
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]
    language = language_data if language_data else DEFAULT_LANGUAGE

    if triggered == "draw-button":
        with capture_logs_to_progress(set_progress) as cap:
            values = selected_values or []
        if not isinstance(values, list):
            values = [values]
        selected_variables = selected_variables or []
        # drop group separators in the variables selector
        selected_variables = [v for v in selected_variables if v not in {"__SEP__BASE__", "__SEP__COM__", "__SEP__SPE__"}]

        if not (isinstance(start_year, int) and isinstance(end_year, int)):
            return no_update, get_text("error_valid_years", language), no_update
        if start_year > end_year:
            return no_update, get_text("error_year_range", language), no_update

        selected_indexes = extract_selected_indexes(values)
        selected_ciks = expand_selected_values(values)

        cap.set_status("Zpracování výběru... / Processing selection...")
        if not selected_ciks and not selected_indexes:
            return no_update, get_text("error_select_company", language), no_update

        use_yahoo = bool(yahoo_state and ((isinstance(yahoo_state, list) and len(yahoo_state) > 0) or yahoo_state is True))

# Check for single company or sector selection
        single_view_content = None
        
        # Helper to check if it's a sector
        is_sector = False
        sector_slug = None
        if selected_ciks and len(selected_ciks) == 1:
            possible_slug = list(selected_ciks)[0]
            if possible_slug.startswith(("SECTOR_", "SUBIND_")):
                is_sector = True
                sector_slug = possible_slug

        # --- Case C: Two sectors selected — Q3 cross-sector correlation ---
        two_sectors = []
        if selected_ciks and len(selected_ciks) == 2 and not selected_indexes:
            two_sectors = [s for s in selected_ciks if str(s).startswith(("SECTOR_", "SUBIND_"))]
        if len(two_sectors) == 2:
            slug_a, slug_b = two_sectors[0], two_sectors[1]
            label_a = PRESET_SOURCES.get(slug_a, {}).get("label", slug_a)
            label_b = PRESET_SOURCES.get(slug_b, {}).get("label", slug_b)
            cs_dates, cs_vals = calculate_cross_sector_correlation(slug_a, slug_b, start_year, end_year)
            q3_fig = go.Figure()
            if cs_dates:
                q3_fig.add_trace(go.Scatter(
                    x=cs_dates, y=cs_vals, mode='lines',
                    name=f'Rolling Corr ({label_a} vs {label_b})',
                    line=dict(color='#A78BFA', width=2)
                ))
                q3_fig.add_hline(y=0, line_dash="dash", line_color="gray")
                # COVID shading
                q3_fig.add_vrect(
                    x0="2020-01-01", x1="2021-03-31",
                    fillcolor="red", opacity=0.1,
                    layer="below", line_width=0,
                    annotation_text="COVID", annotation_position="top left"
                )
            q3_fig.update_layout(
                title=f"Q3 ─ Cross-Sector Correlation: {label_a} vs {label_b} (60-day rolling)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=350,
                yaxis=dict(range=[-1, 1], title="Pearson r"),
                margin=dict(l=40, r=20, t=70, b=20)
            )
            single_view_content = html.Div([
                html.H5(f"Cross-Sector Analysis: {label_a} × {label_b}",
                        style={"color": "white", "marginBottom": "10px"}),
                dcc.Graph(figure=q3_fig, config={'displayModeBar': True})
            ])

        if selected_ciks and len(selected_ciks) == 1 and not selected_indexes:
            # Case A: Single Company
            if not is_sector:
                cik = list(selected_ciks)[0]
                # Q4: R&D/CAPEX card
                rd_card = generate_rd_capex_card(cik, start_year, end_year)
                single_view_content = dbc.Row([
                    dbc.Col(generate_price_card(cik, start_year, end_year), width=12, lg=6),
                    dbc.Col([
                        generate_eps_card(cik, start_year, end_year),
                        generate_pe_card(cik, start_year, end_year),
                        rd_card
                    ], width=12, lg=6)
                ], className="mb-4")
            
            # Case B: Single Sector
            else:
                # 1. Calc Sector Index (Price)
                sec_dates, sec_vals = calculate_sector_stats(sector_slug, start_year, end_year)
                
                # 2. Compare with SPX (reference)
                spx_dates, spx_vals = info_picker_2.yf_download_series_xy("^SPX", start_year, end_year) or ([], [])
                
                # 3. Correlation
                corr_fig = go.Figure()
                if sec_dates and spx_dates:
                     c_dates, c_vals = calculate_correlation(sec_dates, sec_vals, spx_dates, spx_vals)
                     
                     corr_fig.add_trace(go.Scatter(
                         x=c_dates, y=c_vals, mode='lines', 
                         name='Rolling Corr (Sector vs SPX)',
                         line=dict(color='#FACC15', width=2)
                     ))
                     corr_fig.add_hline(y=0, line_dash="dash", line_color="gray")
                     corr_fig.update_layout(
                        title="Sector Correlation with S&P 500 (30-day rolling)",
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=300,
                        yaxis=dict(range=[-1, 1], title="Correlation"),
                        margin=dict(l=40, r=20, t=70, b=20)
                     )

                # 4. Decline Share — dual equal-weight vs market-cap-weight (Q2 fix)
                dec_years, eq_rates, mc_rates = calculate_marketcap_weighted_decline_share(
                    sector_slug, start_year, end_year
                )
                decline_fig = go.Figure()
                decline_fig.add_trace(go.Bar(
                    x=dec_years, y=eq_rates,
                    name='Equal-Weight %',
                    marker_color='#F87171',
                    opacity=0.75
                ))
                decline_fig.add_trace(go.Bar(
                    x=dec_years, y=mc_rates,
                    name='Market-Cap Weighted %',
                    marker_color='#FB923C',
                    opacity=0.95
                ))
                decline_fig.update_layout(
                    title="Companies with Negative Yearly Return (Equal-Weight vs Market-Cap Weighted)",
                    barmode='group',
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=320,
                    yaxis=dict(range=[0, 100], title="% Declined"),
                    legend=dict(x=0, y=1.12, orientation='h'),
                    margin=dict(l=40, r=20, t=70, b=20)
                )
                
                # 5. Advanced Analysis (If a variable is selected)
                adv_rows = []
                if selected_variables and len(selected_variables) > 0:
                    target_var = selected_variables[0]  # Take the first one
                    
                    # A. Growth Correlation (Dual Axis)
                    df_growth = calculate_aggregated_indicator_growth(sector_slug, target_var, start_year, end_year)
                    df_price = calculate_sector_price_growth(sector_slug, start_year, end_year)
                    
                    if not df_growth.empty and not df_price.empty:
                        # Join on index (Date)
                        df_corr = df_growth.join(df_price, lsuffix='_Ind', rsuffix='_Price').dropna()
                        
                        if not df_corr.empty:
                            corr_coef = df_corr['Growth_Ind'].corr(df_corr['Growth_Price'])
                            
                            adv_fig1 = go.Figure()
                            # Indicator Growth (Bars)
                            adv_fig1.add_trace(go.Bar(
                                x=df_corr.index, 
                                y=df_corr['Growth_Ind'],
                                name=f"{target_var} Growth (YoY)",
                                marker_color='#60A5FA',
                                opacity=0.6
                            ))
                            # Price Growth (Line)
                            adv_fig1.add_trace(go.Scatter(
                                x=df_corr.index,
                                y=df_corr['Growth_Price'],
                                name="Sector Price Growth (YoY)",
                                mode='lines+markers',
                                line=dict(color='#F59E0B', width=3),
                                yaxis='y2'
                            ))
                            
                            adv_fig1.update_layout(
                                title=f"Correlation: {target_var} vs. Sector Price (r={corr_coef:.2f})",
                                template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                height=350,
                                yaxis=dict(title=f"{target_var} Growth %"),
                                yaxis2=dict(
                                    title="Price Growth %",
                                    overlaying='y',
                                    side='right',
                                    showgrid=False
                                ),
                                legend=dict(x=0, y=1.1, orientation="h"),
                                margin=dict(l=40, r=40, t=70, b=20)
                            )
                            
                            # Highlight COVID (approx Q1 2020 - Q1 2021)
                            adv_fig1.add_vrect(
                                x0="2020-01-01", x1="2021-03-31",
                                fillcolor="red", opacity=0.1,
                                layer="below", line_width=0,
                                annotation_text="COVID", annotation_position="top left"
                            )
                            
                            # B. Impact Scatter (Decline % vs Price Return)
                            # We need quarter-by-quarter comparison of % Declining Companies vs Sector Return
                            # Re-using decline share logic but quarterly is expensive/complex. 
                            # MVP: Use the aggregated yearly data if available or just skip for now.
                            # Let's approximate using the DataFrames we have: 
                            # X-axis: Indicator Growth (Inverse of decline?), Y-axis: Price Growth
                            
                            adv_fig2 = go.Figure()
                            adv_fig2.add_trace(go.Scatter(
                                x=df_corr['Growth_Ind'],
                                y=df_corr['Growth_Price'],
                                mode='markers',
                                text=[f"{d.year}-Q{d.quarter}" for d in df_corr.index],
                                marker=dict(
                                    size=10,
                                    color=df_corr['Growth_Price'], # Color by price return
                                    colorscale='RdYlGn',
                                    showscale=True
                                ),
                                hovertemplate="Date: %{text}<br>Ind Growth: %{x:.1f}%<br>Price Growth: %{y:.1f}%<extra></extra>"
                            ))
                            
                            # Trendline
                            try:
                                m, b = np.polyfit(df_corr['Growth_Ind'], df_corr['Growth_Price'], 1)
                                line_x = np.array([df_corr['Growth_Ind'].min(), df_corr['Growth_Ind'].max()])
                                line_y = m * line_x + b
                                adv_fig2.add_trace(go.Scatter(
                                    x=line_x, y=line_y, mode='lines', 
                                    line=dict(color='gray', dash='dash'),
                                    name='Trend'
                                ))
                            except: pass

                            adv_fig2.update_layout(
                                title=f"Impact Analysis: {target_var} vs Price Return",
                                template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                height=350,
                                xaxis=dict(title=f"{target_var} Growth % (YoY)"),
                                yaxis=dict(title="Sector Price Growth % (YoY)"),
                                margin=dict(l=40, r=20, t=60, b=20),
                                showlegend=False
                            )
                            
                            adv_rows.append(dbc.Row([
                                dbc.Col(dcc.Graph(figure=adv_fig1, config={'displayModeBar': True}), width=12, lg=7),
                                dbc.Col(dcc.Graph(figure=adv_fig2, config={'displayModeBar': True}), width=12, lg=5)
                            ], className="mb-4"))

                single_view_content = html.Div([
                    dbc.Row([
                        dbc.Col(dcc.Graph(figure=corr_fig, config={'displayModeBar': True}), width=12, md=6),
                        dbc.Col(dcc.Graph(figure=decline_fig, config={'displayModeBar': True}), width=12, md=6)
                    ], style={"marginBottom": "20px"}),
                    html.Div(adv_rows)
                ])

        cap.set_status("Vykreslování grafu... / Drawing graph...")
        fig = generate_graph(
            selected_ciks=selected_ciks,
            selected_variables=selected_variables,
            selected_indexes=selected_indexes,
            start_year=start_year,
            end_year=end_year,
            use_yahoo=use_yahoo,
            language=language,
            set_progress=cap.set_status,
            log_func=cap.log
        )
        cap.set_status("") # Clear progress when done
        return fig, "", single_view_content

    return no_update, no_update, no_update


# ----------------------------- APP LAYOUT ----------------------------------
app.layout = html.Div([
    dcc.Store(id='language-store', data=DEFAULT_LANGUAGE),
    html.Div([
        # Header Row
        html.Div([
            html.H1(id='main-title', children=get_text("title"), style={
                "textAlign": "center",
                "marginBottom": "30px",
                "display": "inline-block",
                "width": "calc(100% - 150px)"
            }),
            html.Button(
                id='language-button',
                children=get_text("language_button"),
                n_clicks=0,
                style={
                    "backgroundColor": "#6c757d",
                    "color": "white",
                    "border": "none",
                    "padding": "8px 16px",
                    "borderRadius": "5px",
                    "cursor": "pointer",
                    "float": "right",
                    "marginTop": "10px"
                }
            )
        ], style={"width": "100%", "marginBottom": "30px"}),

        # Control Panel (Top Half)
        html.Div([
            html.Div([
                html.H6(id='select-company-label', children=get_text("select_company")),
                dcc.Dropdown(
                    id='company-dropdown',
                    options=build_company_dropdown_options(),
                    multi=True,
                    placeholder=get_text("select_company_placeholder"),
                    style={"color": "black"}
                ),
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.H6(id='select-variables-graph-label', children=get_text("select_variables_graph")),
                dcc.Dropdown(
                    id='variable-dropdown',
                    options=build_variable_dropdown_options(),
                    multi=True,
                    placeholder=get_text("select_variables_placeholder"),
                    style={"color": "black"}
                ),
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.H6(id='year-range-label', children=get_text("year_range")),
                html.Div([
                    dcc.Input(id='year-start-input', type='number', step=1, value=YEAR_RANGE["start"],
                              placeholder=get_text("from_year"), style={'marginRight': '20px', 'width': '100px'}),
                    dcc.Input(id='year-end-input', type='number', step=1, value=YEAR_RANGE["end"],
                              placeholder=get_text("to_year"), style={'marginRight': '20px', 'width': '100px'}),
                    dcc.Checklist(
                        id='yahoo-checkbox',
                        options=[{'label': get_text("include_yahoo"), 'value': 'yahoo'}],
                        value=[],
                        inputStyle={"marginRight": "5px", "marginLeft": "20px"},
                        style={"color": "white"}
                    ),
                ], style={'display': 'flex', 'alignItems': 'center'}),
            ], style={'marginBottom': '20px'}),

            html.Button(id='draw-button', children=get_text("update_period"), n_clicks=0, style={
                "backgroundColor": "#2D8CFF",
                "color": "white",
                "border": "none",
                "padding": "10px 20px",
                "borderRadius": "5px",
                "cursor": "pointer",
                "marginBottom": "20px"
            }),
            html.Div(id="loading-progress", style={
                "color": "orange", 
                "fontSize": "20px", 
                "fontWeight": "bold",
                "position": "fixed",
                "top": "60%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "zIndex": 999999,
                "textShadow": "0px 0px 8px rgba(0,0,0,0.8)"
            }),
            html.Pre(id="loading-log", style={
                "color": "lightgreen",
                "fontSize": "14px",
                "position": "fixed",
                "top": "65%",
                "left": "50%",
                "transform": "translateX(-50%)",
                "zIndex": 999999,
                "textShadow": "0px 0px 5px rgba(0,0,0,0.8)",
                "whiteSpace": "pre-wrap",
                "textAlign": "center",
                "maxWidth": "80%"
            }),

            html.Div(id='error-message', style={'color': 'red', 'marginBottom': '20px'}),
            html.Div(id='single-company-view', style={'marginBottom': '30px'}),
        ], style={'maxWidth': '1200px', 'margin': '0 auto'}),

        # Visualization & Table Panel (Bottom Half - Animated)
        dcc.Loading(
            fullscreen=True,
            overlay_style={
                "visibility":"visible",
                "filter": "blur(3px)",
                "backgroundColor": "rgba(15,17,21,0.55)",
            },
            type="graph",
            color="#2D8CFF",
            children=[
                html.Div([
                    dcc.Graph(
                        id='filing-graph',
                        style={"width": "100%"},
                        figure=go.Figure(layout={
                            "template": "plotly_dark",
                            "paper_bgcolor": "#000000",
                            "plot_bgcolor": "#000000",
                            "title": get_text("empty_graph_title"),
                            "xaxis_title": get_text("empty_graph_xaxis"),
                            "yaxis_title": get_text("empty_graph_yaxis")
                        })
                    ),
                    
                    html.H3(id='indicators-table-title', children=get_text("indicators_table"), style={"marginTop": "40px", "color": "white"}),

                    html.Div([
                        html.H6(id='select-variables-table-label', children=get_text("select_variables_table")),
                        dcc.Dropdown(
                            id='table-variables-dropdown',
                            options=build_table_variable_options(),
                            multi=True,
                            placeholder=get_text("select_variables_table_placeholder"),
                            style={"color": "black"}
                        )
                    ], style={'marginBottom': '10px'}),

                    html.Button(
                        id='update-table-button',
                        children=get_text("update_table"),
                        n_clicks=0,
                        style={
                            "backgroundColor": "#2D8CFF",
                            "color": "white",
                            "border": "none",
                            "padding": "10px 20px",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                            "marginBottom": "20px"
                        }
                    ),

                    dash_table.DataTable(
                        id='summary-table',
                        export_format='csv',
                        columns=summary_columns,
                        data=summary_data,
                        fixed_rows={'headers': True},
                        sort_action='native',
                        filter_action='native',
                        sort_mode="multi",
                        page_action='none',
                        style_table={'maxHeight': '500px', 'overflowY': 'auto', 'overflowX': 'auto',
                                     'border': '1px solid #444'},
                        style_cell={'textAlign': 'left', 'padding': '6px', 'backgroundColor': '#222',
                                    'color': '#e9ecef', 'border': '1px solid #444'},
                        style_header={'backgroundColor': '#2a2a2a', 'color': '#e9ecef', 'fontWeight': 'bold',
                                      'border': '1px solid #444'},
                    )
                ], style={'maxWidth': '1200px', 'margin': '40px auto'})
            ]
        )
    ])
])


# ----------------------------- TABLE CALLBACK ------------------------------
@app.callback(
    [Output('summary-table', 'columns'),
     Output('summary-table', 'data')],
    Input('update-table-button', 'n_clicks'),
    State('table-variables-dropdown', 'value'),
    State('company-dropdown', 'value'),
    State('year-start-input', 'value'),
    State('year-end-input', 'value'),
    State('yahoo-checkbox', 'value'),
    prevent_initial_call=True
)
def update_summary_table(n_clicks, selected_vars, unified_values, start_year, end_year, use_yahoo):
    if not selected_vars:
        selected_vars = list(VARIABLES)
    else:
        selected_vars = [v for v in selected_vars if v not in {"__SEP__BASE__", "__SEP__COM__", "__SEP__SPE__"}]

    values = unified_values or []
    if not isinstance(values, list):
        values = [values]

    selected_indexes = extract_selected_indexes(values)
    selected_ciks = expand_selected_values(values)
    
    # Safe defaults if years are empty
    sy = start_year if isinstance(start_year, int) else YEAR_RANGE["start"]
    ey = end_year if isinstance(end_year, int) else YEAR_RANGE["end"]
    year_range = [sy, ey]

    use_yahoo = bool(use_yahoo and ((isinstance(use_yahoo, list) and len(use_yahoo) > 0) or use_yahoo is True))

    df = load_summary_table(selected_vars, selected_ciks, selected_indexes, year_range, use_yahoo)

    if df is None or df.empty:
        return [], []

    base_cols = ["CIK", "Ticker", "Company", "Date"]
    columns = []
    for col in df.columns:
        if col in base_cols:
            columns.append({"name": col, "id": col})
        else:
            # Keep acronyms as-is; others title-case
            if col in RATIO_VARIABLES or col in SPECIAL_VARIABLES or str(col).startswith("Index"):
                columns.append({"name": col, "id": col, "type": "numeric"})
            else:
                columns.append({"name": col.title(), "id": col, "type": "numeric"})

    data = df.to_dict("records")
    return columns, data


# ----------------------------- RUN SERVER ----------------------------------
if __name__ == '__main__':
    if "WindowsApps" in sys.executable:
        raise RuntimeError("Debugger používá python.exe z WindowsApps – nepodporováno.")
    print("[INFO] Launching background Yahoo data pre-fetch thread...")
    info_picker_2.start_yahoo_preload()
    app.run_server(debug=True, port=8050)
