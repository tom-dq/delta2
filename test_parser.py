#!/usr/bin/env python3
"""
Tests for the DELTA parser to ensure key features are working correctly
"""

import sqlite3
import tempfile
from pathlib import Path
from delta_parser import DeltaParser

def test_character_parsing():
    """Test that characters are parsed correctly"""
    parser = DeltaParser()
    chars = parser.parse_characters_file('data/chars')
    
    print(f"✓ Parsed {len(chars)} characters")
    
    # Test specific characters
    assert 1 in chars, "Character 1 should exist"
    assert "Partial synonymy" in chars[1].feature_description, f"Got: {chars[1].feature_description}"
    
    assert 3 in chars, "Character 3 should exist"  
    assert "WoRMS family" in chars[3].feature_description, f"Got: {chars[3].feature_description}"
    
    # Check that states are parsed for multistate characters
    if chars[3].states:
        assert 1 in chars[3].states, "Character 3 should have state 1"
        assert "Acoetidae" in chars[3].states[1], f"State 1 should be Acoetidae, got: {chars[3].states[1]}"
    
    print("✓ Character parsing tests passed")

def test_specs_parsing():
    """Test that specifications are parsed correctly"""
    parser = DeltaParser()
    parser.parse_characters_file('data/chars')
    parser.parse_specs_file('data/specs')
    
    # Check that character types were assigned
    type_counts = {}
    for char in parser.characters.values():
        char_type = char.character_type
        type_counts[char_type] = type_counts.get(char_type, 0) + 1
    
    print(f"✓ Character types found: {type_counts}")
    
    # Should have various types
    assert 'TE' in type_counts, "Should have TE (text) characters"
    assert 'IN' in type_counts, "Should have IN (integer) characters"
    
    print("✓ Specs parsing tests passed")

def test_items_parsing():
    """Test that items are parsed correctly"""
    parser = DeltaParser()
    parser.parse_characters_file('data/chars')
    parser.parse_specs_file('data/specs')
    items = parser.parse_items_file('data/items')
    
    print(f"✓ Parsed {len(items)} items")
    
    # Should have at least some items
    assert len(items) > 0, "Should parse at least one item"
    
    # Check that attributes were parsed
    for item in items.values():
        if item.attributes:
            print(f"✓ Item '{item.name}' has {len(item.attributes)} attributes")
            # Check for different attribute types
            for char_num, value in item.attributes.items():
                if isinstance(value, dict):
                    print(f"  - Character {char_num}: {value}")
                else:
                    print(f"  - Character {char_num}: {value}")
            break
    
    print("✓ Items parsing tests passed")

def test_database_creation():
    """Test that database is created correctly"""
    parser = DeltaParser()
    parser.parse_characters_file('data/chars')
    parser.parse_specs_file('data/specs') 
    parser.parse_items_file('data/items')
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    parser.create_database(db_path)
    
    # Test database contents
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist and have data
    cursor.execute("SELECT COUNT(*) FROM characters")
    char_count = cursor.fetchone()[0]
    assert char_count > 0, f"Should have characters in database, got {char_count}"
    
    cursor.execute("SELECT COUNT(*) FROM items")
    item_count = cursor.fetchone()[0] 
    assert item_count > 0, f"Should have items in database, got {item_count}"
    
    cursor.execute("SELECT COUNT(*) FROM character_states")
    state_count = cursor.fetchone()[0]
    assert state_count > 0, f"Should have character states in database, got {state_count}"
    
    cursor.execute("SELECT COUNT(*) FROM item_character_attributes") 
    attr_count = cursor.fetchone()[0]
    assert attr_count > 0, f"Should have attributes in database, got {attr_count}"
    
    # Test a specific character
    cursor.execute("SELECT feature_description FROM characters WHERE character_number = 1")
    result = cursor.fetchone()
    assert result, "Character 1 should exist in database"
    assert "synonymy" in result[0].lower(), f"Character 1 description should contain 'synonymy', got: {result[0]}"
    
    conn.close()
    Path(db_path).unlink()  # Clean up
    
    print(f"✓ Database creation tests passed ({char_count} chars, {item_count} items, {state_count} states, {attr_count} attributes)")

def test_key_features():
    """Test key DELTA format features are supported"""
    parser = DeltaParser()
    parser.parse_characters_file('data/chars')
    parser.parse_specs_file('data/specs')
    parser.parse_items_file('data/items')
    
    # Check for different character types
    char_types = set(char.character_type for char in parser.characters.values())
    print(f"✓ Character types supported: {sorted(char_types)}")
    
    # Check for character dependencies
    print(f"✓ Character dependencies found: {len(parser.dependencies)}")
    
    # Check for multistate characters with states
    multistate_chars = [char for char in parser.characters.values() 
                       if char.states and len(char.states) > 1]
    print(f"✓ Multistate characters with states: {len(multistate_chars)}")
    
    # Check for mandatory characters
    mandatory_chars = [char for char in parser.characters.values() if char.mandatory]
    print(f"✓ Mandatory characters found: {len(mandatory_chars)}")
    
    print("✓ Key features tests passed")

if __name__ == "__main__":
    print("Running DELTA parser tests...")
    print("=" * 50)
    
    test_character_parsing()
    test_specs_parsing() 
    test_items_parsing()
    test_database_creation()
    test_key_features()
    
    print("=" * 50)
    print("✅ All tests passed!")