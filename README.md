# DELTA Intkey Parser

A Python parser for DELTA (DEscription Language for TAxonomy) format files, designed to convert taxonomic descriptions into a queryable SQLite database for intelligent key generation.

Reimplementation of some bits of Delta https://github.com/AtlasOfLivingAustralia/open-delta

## Overview

This project implements the DELTA format specification from https://www.delta-intkey.com/www/standard.htm and creates a SQLite database schema optimized for taxonomic identification keys.

## Features

- **Complete DELTA format support**: Characters, items, specs, dependencies
- **SQLite database**: Optimized schema for key generation queries  
- **Data validation**: Comprehensive test suite ensures parsing accuracy
- **Key optimization**: Built-in views for selecting discriminating characters

## Setup

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   # OR use the provided script:
   source activate.sh
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Parse DELTA files and create database:
```bash
python delta_parser.py
```

### Run tests:
```bash
python test_parser.py
```

### Query the database:
```bash
sqlite3 delta.db
```

## Project Structure

- `delta_parser.py` - Main parser implementation
- `schema.sql` - SQLite database schema  
- `test_parser.py` - Comprehensive test suite
- `data/` - Example DELTA format files
  - `chars` - Character definitions
  - `items` - Taxonomic item descriptions  
  - `specs` - Format specifications
- `requirements.txt` - Python dependencies

## Database Schema

The SQLite database includes:

- **characters** - Character definitions and types
- **character_states** - States for multistate characters
- **character_dependencies** - Character conditional relationships
- **items** - Taxonomic items/taxa
- **item_character_attributes** - Character values for each item
- **Views** for easy querying and key generation

## DELTA Format Support

✅ **Character Types**: TE (text), IN (integer), RN (real), UM/OM (multistate)  
✅ **Pseudo-values**: U (unknown), V (variable), - (not applicable)  
✅ **Range values**: e.g., "8.5-14"  
✅ **Multistate values**: e.g., "1&3&5"  
✅ **Character dependencies**: Conditional character relationships  
✅ **Complex text**: Formatted descriptions with embedded markup

## Next Steps

This implementation covers steps 1-2 of the PLAN.md:
1. ✅ SQLite schema for DELTA intkey format
2. ✅ PyParsing-based parser with tests

Step 3 will implement the query engine using composable CTEs for intelligent key generation.

