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
python3 delta_parser.py
```

### Use the interactive identification key:
```bash
python3 interactive_key.py
```

### Use the CLI for programmatic access:
```bash
python3 delta_cli.py propose          # Get most selective character
python3 delta_cli.py add-filter 1 0   # Add a filter
python3 delta_cli.py state             # Show current state
python3 delta_cli.py --json propose    # JSON output
```

### Query engine demo:
```bash
python3 query_engine.py
```

### Run tests:
```bash
python3 test_parser.py          # Test DELTA parser
python3 test_query_engine.py    # Test query engine
python3 test_cli.py             # Test CLI interface
```

### Query the database directly:
```bash
sqlite3 delta.db
```

## Project Structure

- `delta_parser.py` - Main parser implementation
- `query_engine.py` - Taxonomic key generation engine  
- `interactive_key.py` - Interactive identification interface
- `delta_cli.py` - Command-line interface for programmatic access
- `schema.sql` - SQLite database schema  
- `test_parser.py` - Parser test suite
- `test_query_engine.py` - Query engine test suite
- `test_cli.py` - CLI test suite
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

## Implementation Status

This implementation covers all steps from PLAN.md:

1. ✅ **SQLite schema for DELTA intkey format** - Complete database design
2. ✅ **PyParsing-based parser with tests** - Full DELTA format support  
3. ✅ **Query engine with composable CTEs** - Intelligent key generation
4. ✅ **CLI for character proposals and filter building** - Programmatic interface

### Key Features Implemented:

- **🔍 Character Selection**: Automatic ranking by discriminating power
- **🔗 Composable CTEs**: Progressive query refinement using Common Table Expressions  
- **🎯 Smart Key Generation**: Most selective characters chosen first
- **💬 Interactive Interface**: User-friendly step-by-step identification
- **🤖 Programmatic CLI**: JSON API for automation and integration
- **💾 State Persistence**: Filters persist between CLI calls
- **⚡ Performance Optimized**: Efficient SQLite queries with proper indexing
- **🧪 Comprehensive Tests**: Full test coverage for all components

### Query Engine Architecture:

The query engine uses **composable Common Table Expressions (CTEs)** to build efficient identification keys:

```sql
WITH base_items AS (SELECT * FROM items),
     filter_1 AS (SELECT * FROM base_items WHERE character_46 = 2),  
     filter_2 AS (SELECT * FROM filter_1 WHERE character_61 = 2)
SELECT * FROM filter_2
```

This approach allows:
- **Progressive refinement** - Each step narrows the results
- **Optimal performance** - SQLite optimizes the entire CTE chain
- **Flexible querying** - Easy to add/remove filters dynamically  
- **Character ranking** - Most discriminating characters selected first

