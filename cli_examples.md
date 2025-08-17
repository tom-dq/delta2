# DELTA CLI Examples

This document demonstrates the DELTA CLI functionality with real examples showing how to propose selective characters and build filters.

## Prerequisites

Make sure you have the database created:
```bash
python3 delta_parser.py
```

## Basic Usage Examples

### 1. Starting Fresh - Reset State

```bash
# Clear any existing filters
python3 delta_cli.py reset
```

### 2. Propose Most Selective Character

```bash
# Get the most discriminating character
python3 delta_cli.py propose
```

**Example Output:**
```
🎯 Most selective character:
   Character 1: <Partial synonymy>
   Type: TE
   Selectivity score: 2.00
   Distinct values: 2
   Remaining items: 2

   Possible values:
     1. 0 (1 items)
     2. \i{}Zachsiella nigromaculata\i0{} (Grube, 1878) (1 items)
```

### 3. Add a Filter Based on Character Value

```bash
# Filter by Character 1 = 0 (first option from above)
python3 delta_cli.py add-filter 1 0
```

**Example Output:**
```
✅ Added filter: Character 1 = 0
   Remaining items: 1
   Total filters: 1
   Items:
     • Subadyte sp_Abyss
```

### 4. Check Current State

```bash
# View current filter state
python3 delta_cli.py state
```

**Example Output:**
```
📊 Current Filter State:
   Filters applied: 1
   Remaining items: 1
   Active filters:
     1. Character 1 = 0
   Remaining items:
     • Subadyte sp_Abyss
```

### 5. Try to Propose Next Character

```bash
# Since we're down to 1 item, no more discrimination needed
python3 delta_cli.py propose
```

**Result:** No output (silently succeeds with no candidates)

### 6. Undo Last Filter

```bash
# Remove the last applied filter
python3 delta_cli.py undo
```

**Example Output:**
```
↶ Removed filter: Character 1 = 0
   Remaining items: 2
```

## JSON Output Examples

All commands support JSON output for programmatic use:

### JSON Propose Character

```bash
python3 delta_cli.py --json propose
```

**Example Output:**
```json
{
  "status": "success",
  "character": {
    "number": 1,
    "description": "<Partial synonymy>",
    "type": "TE",
    "distinct_values": 2,
    "selectivity_score": 2.0
  },
  "possible_values": [
    {
      "value": 0,
      "description": "0",
      "item_count": 1
    },
    {
      "value": "\\i{}Zachsiella nigromaculata\\i0{} (Grube, 1878)",
      "description": "\\i{}Zachsiella nigromaculata\\i0{} (Grube, 1878)",
      "item_count": 1
    }
  ],
  "remaining_items": 2,
  "current_filters": 0
}
```

### JSON Add Filter

```bash
python3 delta_cli.py --json add-filter 1 0
```

**Example Output:**
```json
{
  "status": "success",
  "message": "Added filter: Character 1 = 0",
  "remaining_items": 1,
  "total_filters": 1,
  "items": [
    "\\i{}Subadyte\\i0{} sp_Abyss"
  ]
}
```

### JSON State

```bash
python3 delta_cli.py --json state
```

**Example Output:**
```json
{
  "filters": [
    {
      "character_number": 1,
      "value": 0,
      "description": "Character 1 = 0"
    }
  ],
  "current_items": [
    {
      "id": 2,
      "item_name": "\\i{}Subadyte\\i0{} sp_Abyss",
      "item_number": 2
    }
  ],
  "remaining_count": 1,
  "available_characters": []
}
```

## Advanced Examples

### Building Complex Filters Step by Step

```bash
# Start fresh
python3 delta_cli.py reset

# Step 1: Get initial recommendation
python3 delta_cli.py propose

# Step 2: Apply first filter
python3 delta_cli.py add-filter 1 "\\i{}Zachsiella nigromaculata\\i0{} (Grube, 1878)"

# Step 3: Check what's left
python3 delta_cli.py state

# Step 4: See if more discrimination needed
python3 delta_cli.py propose
```

### Excluding Characters from Proposals

```bash
# Exclude character 1 from proposals
python3 delta_cli.py propose --exclude 1

# Exclude multiple characters
python3 delta_cli.py propose --exclude 1 2 3
```

### Working with Different Value Types

```bash
# Integer values
python3 delta_cli.py add-filter 46 2

# Float values  
python3 delta_cli.py add-filter 155 12.5

# String values (quoted if they contain spaces)
python3 delta_cli.py add-filter 4 "specimen_name"
```

## Error Handling Examples

### Non-existent Character

```bash
python3 delta_cli.py add-filter 99999 1
```

**Output:**
```
❌ Character 99999 not found
```

### No Database

```bash
python3 delta_cli.py --db nonexistent.db propose
```

**Output:**
```
❌ Database file 'nonexistent.db' not found.
Run 'python3 delta_parser.py' first to create the database.
```

## Programmatic Workflow Examples

### Bash Script for Automated Filtering

```bash
#!/bin/bash
# automated_key.sh - Build an identification key automatically

# Reset to start fresh
python3 delta_cli.py reset

# Get first character and filter automatically
CHAR_INFO=$(python3 delta_cli.py --json propose)
CHAR_NUM=$(echo "$CHAR_INFO" | jq -r '.character.number')
FIRST_VALUE=$(echo "$CHAR_INFO" | jq -r '.possible_values[0].value')

# Apply first filter
python3 delta_cli.py add-filter "$CHAR_NUM" "$FIRST_VALUE"

# Check result
python3 delta_cli.py state
```

### Python Script for Complex Logic

```python
#!/usr/bin/env python3
# automated_key.py - Build keys with custom logic

import subprocess
import json

def run_cli(cmd):
    """Run CLI command and return JSON result"""
    result = subprocess.run(
        f"python3 delta_cli.py --json {cmd}".split(),
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

# Reset state
run_cli("reset")

# Build key until single item or no candidates
while True:
    # Get proposal
    proposal = run_cli("propose")
    
    if proposal['status'] != 'success':
        print(f"Finished: {proposal['message']}")
        break
    
    # Pick first value
    char_num = proposal['character']['number']
    first_value = proposal['possible_values'][0]['value']
    
    # Apply filter
    result = run_cli(f"add-filter {char_num} {first_value}")
    print(f"Applied: Character {char_num} = {first_value}")
    print(f"Remaining: {result['remaining_items']} items")
    
    if result['remaining_items'] <= 1:
        break

# Show final state
state = run_cli("state")
print(f"Final result: {state['remaining_count']} items")
```

## State Persistence

The CLI automatically saves state between calls in `.delta_cli_state.json`. This allows you to:

1. **Build filters across multiple CLI calls**
2. **Resume work after interruption**  
3. **Share filter state between different tools**

To start completely fresh, use:
```bash
python3 delta_cli.py reset
# or manually delete the state file
rm .delta_cli_state.json
```

## Integration with Other Tools

The CLI is designed to work well with:

- **Shell scripts** (bash, zsh)
- **JSON processing tools** (jq, python)
- **Workflow automation** (GitHub Actions, CI/CD)
- **Web applications** (via subprocess calls)

The consistent JSON output format makes it easy to integrate into larger systems.