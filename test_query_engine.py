#!/usr/bin/env python3
"""
Tests for the DELTA Query Engine

This module tests the taxonomic key generation functionality,
composable CTE queries, and interactive key features.
"""

import tempfile
import sqlite3
from pathlib import Path
from query_engine import TaxonomicQueryEngine, CharacterInfo
from delta_parser import DeltaParser


def setup_test_database():
    """Create a test database with sample data"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Parse the real data and create database
    parser = DeltaParser()
    parser.parse_characters_file('data/chars')
    parser.parse_specs_file('data/specs')
    parser.parse_items_file('data/items')
    parser.create_database(db_path)
    
    return db_path


def test_character_rankings():
    """Test character ranking and selectivity scoring"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            characters = engine.get_character_rankings()
            
            print(f"✓ Retrieved {len(characters)} ranked characters")
            
            # Check that characters are properly ranked
            assert len(characters) > 0, "Should have at least one character"
            
            # Check that characters have proper selectivity scores
            for char in characters[:5]:
                assert char.distinct_values > 0, f"Character {char.number} should have distinct values"
                assert char.coding_completeness > 0, f"Character {char.number} should have completeness > 0"
                assert char.selectivity_score >= 0, f"Character {char.number} should have valid selectivity score"
            
            # Check that they're properly sorted (higher selectivity first)
            for i in range(len(characters) - 1):
                assert characters[i].selectivity_score >= characters[i+1].selectivity_score, \
                    "Characters should be sorted by selectivity score"
            
            print(f"✓ Character ranking tests passed")
            print(f"  Top character: {characters[0].number} - {characters[0].description[:50]}...")
            print(f"  Selectivity score: {characters[0].selectivity_score:.2f}")
            
    finally:
        Path(db_path).unlink()


def test_character_values():
    """Test retrieval of character values and descriptions"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            # Get best character
            characters = engine.get_character_rankings()
            best_char = characters[0]
            
            # Get its values
            values = engine.get_character_values(best_char.number)
            
            print(f"✓ Retrieved {len(values)} values for character {best_char.number}")
            
            assert len(values) > 0, "Should have at least one value"
            
            # Check value structure
            for value, description, count in values:
                assert count > 0, f"Value {value} should have count > 0"
                assert description is not None, f"Value {value} should have description"
                
            print(f"✓ Character values tests passed")
            print(f"  Example value: {values[0][1]} ({values[0][2]} items)")
            
    finally:
        Path(db_path).unlink()


def test_progressive_querying():
    """Test the composable CTE querying system"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            # Get initial item count
            cursor = engine.conn.execute("SELECT COUNT(*) as count FROM items")
            initial_count = cursor.fetchone()['count']
            
            # Get best character and its first value
            characters = engine.get_character_rankings()
            best_char = characters[0]
            values = engine.get_character_values(best_char.number)
            first_value = values[0][0]
            
            # Query by first character
            result = engine.query_items_by_character(best_char.number, first_value)
            
            print(f"✓ Progressive query: {initial_count} → {len(result.matching_items)} items")
            
            # Should have fewer items (or same if only one value)
            assert len(result.matching_items) <= initial_count, \
                "Filtering should not increase item count"
            
            # Should have valid SQL
            assert "WITH" in result.query_sql, "Should use CTE-based query"
            assert "SELECT" in result.query_sql, "Should be valid SQL"
            
            # Test progressive refinement if possible
            if len(result.matching_items) > 1 and result.character_candidates:
                next_char = result.character_candidates[0]
                next_values = engine.get_character_values(
                    next_char.number, 
                    [item['item_number'] for item in result.matching_items]
                )
                
                if next_values:
                    # Apply second filter
                    result2 = engine.query_items_by_character(
                        next_char.number, next_values[0][0], 
                        [(best_char.number, first_value)]
                    )
                    
                    print(f"✓ Second refinement: {len(result.matching_items)} → {len(result2.matching_items)} items")
                    
                    # Should further reduce (or stay same)
                    assert len(result2.matching_items) <= len(result.matching_items), \
                        "Second filter should not increase items"
            
            print(f"✓ Progressive querying tests passed")
            
    finally:
        Path(db_path).unlink()


def test_cte_query_structure():
    """Test that CTE queries are properly structured"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            characters = engine.get_character_rankings()
            char = characters[0]
            values = engine.get_character_values(char.number)
            
            if values:
                # Test single filter
                result = engine.query_items_by_character(char.number, values[0][0])
                
                # Check CTE structure
                sql = result.query_sql
                assert sql.count("WITH") == 1, "Should have exactly one WITH clause"
                assert "base_items AS" in sql, "Should have base_items CTE"
                assert "filter_1 AS" in sql, "Should have filter_1 CTE"
                
                # Test multiple filters
                if len(values) > 1 and result.character_candidates:
                    next_char = result.character_candidates[0]
                    next_values = engine.get_character_values(next_char.number)
                    
                    if next_values:
                        result2 = engine.query_items_by_character(
                            next_char.number, next_values[0][0],
                            [(char.number, values[0][0])]
                        )
                        
                        sql2 = result2.query_sql
                        assert "filter_1 AS" in sql2, "Should have filter_1 CTE"
                        assert "filter_2 AS" in sql2, "Should have filter_2 CTE"
                        
                print(f"✓ CTE query structure tests passed")
                
    finally:
        Path(db_path).unlink()


def test_key_generation():
    """Test automatic identification key generation"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            key_steps = engine.generate_identification_key(max_steps=5)
            
            print(f"✓ Generated identification key with {len(key_steps)} steps")
            
            # Should have at least one step if there are multiple items
            cursor = engine.conn.execute("SELECT COUNT(*) FROM items")
            item_count = cursor.fetchone()[0]
            
            if item_count > 1:
                assert len(key_steps) > 0, "Should generate at least one key step"
                
                # Check step structure
                for i, step in enumerate(key_steps):
                    assert isinstance(step.character, CharacterInfo), \
                        f"Step {i} should have CharacterInfo"
                    assert len(step.possible_values) > 0, \
                        f"Step {i} should have possible values"
                    assert step.remaining_items > 0, \
                        f"Step {i} should have remaining items count"
                    assert "WITH" in step.query_cte, \
                        f"Step {i} should have CTE query"
                        
                print(f"✓ Key generation tests passed")
                print(f"  First step character: {key_steps[0].character.description[:40]}...")
                print(f"  Possible values: {len(key_steps[0].possible_values)}")
            else:
                print(f"✓ Key generation tests passed (single item, no key needed)")
                
    finally:
        Path(db_path).unlink()


def test_character_info_retrieval():
    """Test character information retrieval"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            # Test getting character info
            char_info = engine.get_character_info(1)  # Character 1 should exist
            
            if char_info:
                assert char_info.number == 1, "Should return correct character number"
                assert char_info.description is not None, "Should have description"
                assert char_info.character_type in ['TE', 'IN', 'RN', 'UM', 'OM'], \
                    "Should have valid character type"
                
                print(f"✓ Character info retrieval tests passed")
                print(f"  Character 1: {char_info.description[:50]}...")
                print(f"  Type: {char_info.character_type}")
                
                # Test multistate character states
                if char_info.character_type in ('UM', 'OM') and char_info.states:
                    assert isinstance(char_info.states, dict), "States should be dictionary"
                    assert len(char_info.states) > 0, "Should have at least one state"
                    print(f"  States: {len(char_info.states)} defined")
            else:
                print("✓ Character info retrieval tests passed (character 1 not found)")
                
            # Test non-existent character
            missing_char = engine.get_character_info(99999)
            assert missing_char is None, "Should return None for non-existent character"
            
    finally:
        Path(db_path).unlink()


def test_query_performance():
    """Test query performance and optimization"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            import time
            
            # Test character ranking performance
            start_time = time.time()
            characters = engine.get_character_rankings()
            ranking_time = time.time() - start_time
            
            assert ranking_time < 5.0, f"Character ranking should be fast, took {ranking_time:.2f}s"
            
            # Test query performance
            if characters:
                char = characters[0]
                values = engine.get_character_values(char.number)
                
                if values:
                    start_time = time.time()
                    result = engine.query_items_by_character(char.number, values[0][0])
                    query_time = time.time() - start_time
                    
                    assert query_time < 2.0, f"Item query should be fast, took {query_time:.2f}s"
                    
            print(f"✓ Query performance tests passed")
            print(f"  Character ranking: {ranking_time:.3f}s")
            print(f"  Item query: {query_time:.3f}s" if 'query_time' in locals() else "")
            
    finally:
        Path(db_path).unlink()


def test_edge_cases():
    """Test edge cases and error conditions"""
    db_path = setup_test_database()
    
    try:
        with TaxonomicQueryEngine(db_path) as engine:
            # Test empty filters
            result = engine.query_items_by_character(999999, "nonexistent")  # Non-existent character
            assert len(result.matching_items) == 0, "Non-existent character should return no items"
            
            # Test excluded characters
            all_chars = engine.get_character_rankings()
            if len(all_chars) > 1:
                excluded = {all_chars[0].number}
                filtered_chars = engine.get_character_rankings(excluded_chars=excluded)
                assert all_chars[0].number not in [c.number for c in filtered_chars], \
                    "Excluded character should not appear in results"
                
            # Test character values for non-existent character
            values = engine.get_character_values(999999)
            assert len(values) == 0, "Non-existent character should have no values"
            
            print(f"✓ Edge case tests passed")
            
    finally:
        Path(db_path).unlink()


def run_all_tests():
    """Run all query engine tests"""
    print("DELTA Query Engine Tests")
    print("=" * 50)
    
    tests = [
        test_character_rankings,
        test_character_values, 
        test_progressive_querying,
        test_cte_query_structure,
        test_key_generation,
        test_character_info_retrieval,
        test_query_performance,
        test_edge_cases
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            print(f"\n🧪 Running {test_func.__name__}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All query engine tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)