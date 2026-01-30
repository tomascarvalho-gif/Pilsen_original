# Data Synchronization Guide

This guide explains how to sync downloaded data (`xbrl_data_json/`) between computers.

## Important Note

The `xbrl_data_json/` folder is excluded from Git (in `.gitignore`) because:
- Data files are large (potentially GBs)
- Git is not designed for large binary/data files
- Each computer can download data independently

## Option 1: Manual Copy (Recommended for Small Datasets)

### From Source Computer (where data was downloaded):

```bash
# Create a compressed archive
cd /path/to/OP-screener
tar -czf xbrl_data_backup.tar.gz xbrl_data_json/
```

Or on Windows:
```cmd
cd path\to\OP-screener
tar -czf xbrl_data_backup.tar.gz xbrl_data_json\
```

### Transfer to Target Computer:

- Copy `xbrl_data_backup.tar.gz` via USB drive, cloud storage, or network share

### On Target Computer:

```bash
# Extract the data
cd /path/to/OP-screener
tar -xzf xbrl_data_backup.tar.gz
```

Or on Windows:
```cmd
cd path\to\OP-screener
tar -xzf xbrl_data_backup.tar.gz
```

## Option 2: Network Sync (For Same Network)

### Using rsync (macOS/Linux):

```bash
# From source computer
rsync -avz --progress /path/to/source/OP-screener/xbrl_data_json/ user@target-computer:/path/to/target/OP-screener/xbrl_data_json/
```

### Using robocopy (Windows):

```cmd
robocopy "C:\path\to\source\OP-screener\xbrl_data_json" "\\target-computer\path\to\target\OP-screener\xbrl_data_json" /E /Z
```

## Option 3: Cloud Storage Sync

### Using Google Drive / Dropbox / OneDrive:

1. Upload `xbrl_data_json/` folder to cloud storage
2. Download on target computer
3. Place in project directory

### Using Git LFS (Advanced - for version control):

If you want to track data in Git:

1. Install Git LFS:
   ```bash
   git lfs install
   ```

2. Track JSON files:
   ```bash
   git lfs track "xbrl_data_json/**/*.json"
   ```

3. Add and commit:
   ```bash
   git add .gitattributes
   git add xbrl_data_json/
   git commit -m "Add data files via Git LFS"
   git push
   ```

**Note:** Git LFS requires a GitHub account with LFS quota. Free tier: 1 GB storage, 1 GB bandwidth/month.

## Option 4: Incremental Sync Script

Create a script to sync only new files:

### sync_data.sh (macOS/Linux):

```bash
#!/bin/bash
SOURCE_DIR="/path/to/source/OP-screener/xbrl_data_json"
TARGET_DIR="/path/to/target/OP-screener/xbrl_data_json"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Sync only new/changed files
rsync -avz --update "$SOURCE_DIR/" "$TARGET_DIR/"
```

### sync_data.bat (Windows):

```batch
@echo off
set SOURCE_DIR=C:\path\to\source\OP-screener\xbrl_data_json
set TARGET_DIR=C:\path\to\target\OP-screener\xbrl_data_json

robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /XO /Z
```

## Recommended Approach

For your use case (syncing from download computer to GitHub computer):

1. **Download computer**: After download completes, create archive
2. **Transfer**: Use USB drive, cloud storage, or network
3. **GitHub computer**: Extract to project directory
4. **Verify**: Run `python downloader.py --verify-only` to check data

## Verification After Sync

```bash
# Count files
find xbrl_data_json -name "*.json" | wc -l

# Check specific company
ls xbrl_data_json/AAPL/

# Verify with downloader
python downloader.py --verify-only
```

## File Size Estimates

- Per filing: ~20-50 KB
- Per company (10 years): ~2-4 MB
- 500 companies (10 years): ~1-2 GB

Consider compression when transferring large datasets.
