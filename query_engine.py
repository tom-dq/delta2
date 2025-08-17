#!/usr/bin/env python3
"""
DELTA Query Engine for Taxonomic Key Generation

This module implements an intelligent query engine that uses composable CTEs
to generate taxonomic identification keys by selecting the most discriminating
characters first.
"""

import sqlite3
import json
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass 
class CharacterInfo:
    """Information about a character for key generation"""
    number: int
    description: str
    character_type: str
    distinct_values: int
    coding_completeness: float
    states: Dict[int, str] = None
    
    @property
    def selectivity_score(self) -> float:
        """Calculate selectivity score for character ranking"""
        # Higher distinct values and higher completeness = better character
        return self.distinct_values * self.coding_completeness


@dataclass
class KeyStep:
    """A single step in an identification key"""
    character: CharacterInfo
    possible_values: List[Any]
    remaining_items: int
    query_cte: str


@dataclass 
class QueryResult:
    """Result of a query refinement step"""
    matching_items: List[Dict[str, Any]]
    character_candidates: List[CharacterInfo]
    query_sql: str


class TaxonomicQueryEngine:
    """
    Query engine for generating taxonomic identification keys using 
    composable Common Table Expressions (CTEs) in SQLite
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
    
    def get_character_rankings(self, excluded_chars: Set[int] = None) -> List[CharacterInfo]:
        """
        Get characters ranked by their discriminating power using CTEs
        
        This uses a CTE to calculate selectivity metrics for all characters
        """
        excluded_chars = excluded_chars or set()
        excluded_clause = ""
        if excluded_chars:
            excluded_clause = f"AND c.character_number NOT IN ({','.join(map(str, excluded_chars))})"
            
        query = f"""
        WITH character_metrics AS (
            -- Calculate discriminating power for each character
            SELECT 
                c.character_number,
                c.feature_description,
                c.character_type,
                c.omit_from_key,
                c.mandatory,
                -- Count distinct non-null, non-pseudo values
                COUNT(DISTINCT 
                    CASE 
                        WHEN ica.is_unknown OR ica.is_variable OR ica.is_not_applicable THEN NULL
                        WHEN ica.integer_value IS NOT NULL THEN ica.integer_value
                        WHEN ica.real_value IS NOT NULL THEN ica.real_value  
                        WHEN ica.text_value IS NOT NULL THEN ica.text_value
                        WHEN ica.state_values IS NOT NULL THEN ica.state_values
                        ELSE NULL
                    END
                ) as distinct_values,
                -- Calculate coding completeness (non-pseudo values / total items)
                CAST(COUNT(
                    CASE 
                        WHEN NOT (ica.is_unknown OR ica.is_variable OR ica.is_not_applicable) 
                        THEN 1 
                        ELSE NULL 
                    END
                ) AS REAL) / COUNT(ica.id) as coding_completeness,
                COUNT(ica.id) as total_codings
            FROM characters c
            LEFT JOIN item_character_attributes ica ON c.id = ica.character_id
            WHERE c.omit_from_key = FALSE
                AND c.mandatory = FALSE
                {excluded_clause}
            GROUP BY c.id, c.character_number, c.feature_description, c.character_type
            HAVING coding_completeness > 0.5  -- Only well-coded characters
                AND distinct_values > 1        -- Only characters with variation
        )
        SELECT 
            character_number,
            feature_description,
            character_type,
            distinct_values,
            coding_completeness,
            -- Selectivity score: favor high variation + high completeness
            (distinct_values * coding_completeness) as selectivity_score
        FROM character_metrics
        ORDER BY selectivity_score DESC, distinct_values DESC
        """
        
        cursor = self.conn.execute(query)
        characters = []
        
        for row in cursor:
            # Get character states if it's multistate
            states = None
            if row['character_type'] in ('UM', 'OM'):
                states = self._get_character_states(row['character_number'])
                
            char_info = CharacterInfo(
                number=row['character_number'],
                description=row['feature_description'],
                character_type=row['character_type'],
                distinct_values=row['distinct_values'],
                coding_completeness=row['coding_completeness'],
                states=states
            )
            characters.append(char_info)
            
        return characters
    
    def _get_character_states(self, character_number: int) -> Dict[int, str]:
        """Get states for a multistate character"""
        query = """
        SELECT cs.state_number, cs.state_description
        FROM character_states cs
        JOIN characters c ON cs.character_id = c.id
        WHERE c.character_number = ?
        ORDER BY cs.state_number
        """
        
        cursor = self.conn.execute(query, (character_number,))
        states = {}
        for row in cursor:
            states[row['state_number']] = row['state_description']
        return states
    
    def query_items_by_character(self, character_number: int, value: Any, 
                                previous_filters: List[Tuple[int, Any]] = None) -> QueryResult:
        """
        Query items using composable CTEs for progressive refinement
        
        This builds a chain of CTEs, each filtering based on character values
        """
        previous_filters = previous_filters or []
        
        # Build the CTE chain
        cte_parts = []
        cte_names = []
        
        # Base CTE - all items
        base_cte = """
        base_items AS (
            SELECT DISTINCT i.id, i.item_name, i.item_number
            FROM items i
        )
        """
        cte_parts.append(base_cte)
        current_cte = "base_items"
        
        # Add filter CTEs for previous selections
        for i, (prev_char_num, prev_value) in enumerate(previous_filters):
            filter_cte_name = f"filter_{i+1}"
            filter_cte = self._build_character_filter_cte(
                filter_cte_name, current_cte, prev_char_num, prev_value
            )
            cte_parts.append(filter_cte)
            current_cte = filter_cte_name
        
        # Add filter for current character
        final_filter_name = f"filter_{len(previous_filters)+1}"
        final_filter_cte = self._build_character_filter_cte(
            final_filter_name, current_cte, character_number, value
        )
        cte_parts.append(final_filter_cte)
        
        # Main query to get matching items
        main_query = f"""
        WITH {','.join(cte_parts)}
        SELECT 
            fi.item_name,
            fi.item_number,
            COUNT(*) OVER() as total_matches
        FROM {final_filter_name} fi
        ORDER BY fi.item_name
        """
        
        cursor = self.conn.execute(main_query)
        matching_items = [dict(row) for row in cursor.fetchall()]
        
        # Get next best characters for remaining items
        if matching_items:
            used_characters = {char_num for char_num, _ in previous_filters + [(character_number, value)]}
            character_candidates = self.get_character_rankings(excluded_chars=used_characters)
            
            # Filter candidates to only those that discriminate among remaining items
            character_candidates = self._filter_discriminating_characters(
                character_candidates, [item['item_number'] for item in matching_items]
            )
        else:
            character_candidates = []
        
        return QueryResult(
            matching_items=matching_items,
            character_candidates=character_candidates,
            query_sql=main_query
        )
    
    def _build_character_filter_cte(self, cte_name: str, source_cte: str, 
                                   character_number: int, value: Any) -> str:
        """Build a CTE that filters items by character value"""
        
        # Determine the value matching condition based on type
        if isinstance(value, int):
            value_condition = f"ica.integer_value = {value} OR json_extract(ica.state_values, '$[0]') = {value}"
        elif isinstance(value, float):
            value_condition = f"ica.real_value = {value}"
        elif isinstance(value, str):
            # Escape single quotes for SQL
            escaped_value = value.replace("'", "''")
            value_condition = f"ica.text_value = '{escaped_value}'"
        elif isinstance(value, list):  # Range or multistate
            if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
                # Range query
                min_val, max_val = value
                value_condition = f"""(
                    (ica.range_min <= {max_val} AND ica.range_max >= {min_val}) OR
                    (ica.integer_value BETWEEN {min_val} AND {max_val}) OR  
                    (ica.real_value BETWEEN {min_val} AND {max_val})
                )"""
            else:
                # Multistate query
                state_list = ','.join(map(str, value))
                value_condition = f"""(
                    ica.integer_value IN ({state_list}) OR
                    json_extract(ica.state_values, '$[0]') IN ({state_list})
                )"""
        else:
            # Fallback for complex values
            value_condition = "1=1"  # Match all
            
        cte = f"""
        {cte_name} AS (
            SELECT DISTINCT sc.id, sc.item_name, sc.item_number
            FROM {source_cte} sc
            JOIN item_character_attributes ica ON sc.id = ica.item_id
            JOIN characters c ON ica.character_id = c.id
            WHERE c.character_number = {character_number}
                AND NOT (ica.is_unknown OR ica.is_variable OR ica.is_not_applicable)
                AND ({value_condition})
        )
        """
        return cte
    
    def _filter_discriminating_characters(self, candidates: List[CharacterInfo], 
                                        remaining_item_numbers: List[int]) -> List[CharacterInfo]:
        """Filter characters to only those that discriminate among remaining items"""
        if len(remaining_item_numbers) <= 1:
            return []
            
        discriminating = []
        item_list = ','.join(map(str, remaining_item_numbers))
        
        for char in candidates:
            # Check if this character actually discriminates among remaining items
            query = f"""
            SELECT COUNT(DISTINCT 
                CASE 
                    WHEN ica.is_unknown OR ica.is_variable OR ica.is_not_applicable THEN NULL
                    WHEN ica.integer_value IS NOT NULL THEN ica.integer_value
                    WHEN ica.real_value IS NOT NULL THEN ica.real_value
                    WHEN ica.text_value IS NOT NULL THEN ica.text_value
                    WHEN ica.state_values IS NOT NULL THEN ica.state_values
                    ELSE NULL
                END
            ) as distinct_vals
            FROM item_character_attributes ica
            JOIN characters c ON ica.character_id = c.id
            JOIN items i ON ica.item_id = i.id
            WHERE c.character_number = {char.number}
                AND i.item_number IN ({item_list})
            """
            
            cursor = self.conn.execute(query)
            result = cursor.fetchone()
            if result and result['distinct_vals'] > 1:
                discriminating.append(char)
                
        return discriminating
    
    def get_character_values(self, character_number: int, 
                           item_numbers: List[int] = None) -> List[Tuple[Any, str, int]]:
        """
        Get possible values for a character with counts
        Returns list of (value, description, count) tuples
        """
        item_filter = ""
        if item_numbers:
            item_list = ','.join(map(str, item_numbers))
            item_filter = f"AND i.item_number IN ({item_list})"
        
        query = f"""
        WITH character_values AS (
            SELECT 
                CASE 
                    WHEN ica.is_unknown THEN 'U'
                    WHEN ica.is_variable THEN 'V' 
                    WHEN ica.is_not_applicable THEN '-'
                    WHEN ica.integer_value IS NOT NULL THEN CAST(ica.integer_value AS TEXT)
                    WHEN ica.real_value IS NOT NULL THEN CAST(ica.real_value AS TEXT)
                    WHEN ica.text_value IS NOT NULL THEN ica.text_value
                    WHEN ica.state_values IS NOT NULL THEN ica.state_values
                    WHEN ica.range_min IS NOT NULL THEN 
                        CAST(ica.range_min AS TEXT) || '-' || CAST(ica.range_max AS TEXT)
                    ELSE 'NULL'
                END as value_display,
                CASE 
                    WHEN ica.integer_value IS NOT NULL THEN ica.integer_value
                    WHEN ica.real_value IS NOT NULL THEN ica.real_value
                    WHEN ica.text_value IS NOT NULL THEN ica.text_value
                    WHEN ica.state_values IS NOT NULL THEN json_extract(ica.state_values, '$[0]')
                    ELSE ica.text_value
                END as raw_value,
                i.item_name
            FROM item_character_attributes ica
            JOIN characters c ON ica.character_id = c.id
            JOIN items i ON ica.item_id = i.id
            WHERE c.character_number = {character_number}
                AND NOT (ica.is_unknown OR ica.is_variable OR ica.is_not_applicable)
                {item_filter}
        )
        SELECT 
            raw_value,
            value_display,
            COUNT(*) as item_count,
            GROUP_CONCAT(item_name, '; ') as items
        FROM character_values
        WHERE raw_value IS NOT NULL
        GROUP BY raw_value, value_display
        ORDER BY item_count DESC, value_display
        """
        
        cursor = self.conn.execute(query)
        values = []
        for row in cursor:
            # Convert back to appropriate type
            raw_value = row['raw_value']
            if isinstance(raw_value, str) and raw_value.isdigit():
                raw_value = int(raw_value)
            
            values.append((raw_value, row['value_display'], row['item_count']))
            
        # Add character states if multistate
        char_info = self.get_character_info(character_number)
        if char_info and char_info.states:
            # Replace state numbers with descriptions where possible
            enhanced_values = []
            for value, display, count in values:
                if isinstance(value, int) and value in char_info.states:
                    description = f"{value}. {char_info.states[value]}"
                    enhanced_values.append((value, description, count))
                else:
                    enhanced_values.append((value, display, count))
            return enhanced_values
            
        return values
    
    def get_character_info(self, character_number: int) -> Optional[CharacterInfo]:
        """Get detailed information about a character"""
        query = """
        SELECT c.character_number, c.feature_description, c.character_type
        FROM characters c
        WHERE c.character_number = ?
        """
        
        cursor = self.conn.execute(query, (character_number,))
        row = cursor.fetchone()
        if not row:
            return None
            
        states = None
        if row['character_type'] in ('UM', 'OM'):
            states = self._get_character_states(character_number)
            
        return CharacterInfo(
            number=row['character_number'],
            description=row['feature_description'],
            character_type=row['character_type'],
            distinct_values=0,  # Not calculated here
            coding_completeness=0.0,  # Not calculated here
            states=states
        )
    
    def generate_identification_key(self, max_steps: int = 10) -> List[KeyStep]:
        """
        Generate a complete identification key using the most discriminating characters
        """
        key_steps = []
        current_filters = []
        
        for step in range(max_steps):
            # Get remaining items
            if current_filters:
                result = self.query_items_by_character(
                    current_filters[-1][0], current_filters[-1][1], current_filters[:-1]
                )
                remaining_items = len(result.matching_items)
            else:
                # First step - count all items
                cursor = self.conn.execute("SELECT COUNT(*) as count FROM items")
                remaining_items = cursor.fetchone()['count']
                
            if remaining_items <= 1:
                break
                
            # Get best character for this step
            used_chars = {char_num for char_num, _ in current_filters}
            candidates = self.get_character_rankings(excluded_chars=used_chars)
            
            if not candidates:
                break
                
            best_char = candidates[0]
            
            # Get possible values for this character
            current_items = None
            if current_filters:
                current_items = [item['item_number'] for item in result.matching_items]
                
            possible_values = self.get_character_values(best_char.number, current_items)
            
            # Create CTE for this step
            step_cte = self._generate_step_cte(best_char, current_filters)
            
            key_step = KeyStep(
                character=best_char,
                possible_values=possible_values,
                remaining_items=remaining_items,
                query_cte=step_cte
            )
            key_steps.append(key_step)
            
            # For demonstration, pick the first available value
            if possible_values:
                first_value = possible_values[0][0]
                current_filters.append((best_char.number, first_value))
            else:
                break
                
        return key_steps
    
    def _generate_step_cte(self, character: CharacterInfo, 
                          previous_filters: List[Tuple[int, Any]]) -> str:
        """Generate a CTE for a key step"""
        cte_parts = ["base_items AS (SELECT id, item_name FROM items)"]
        current_cte = "base_items"
        
        for i, (char_num, value) in enumerate(previous_filters):
            filter_name = f"filter_{i+1}"
            filter_cte = self._build_character_filter_cte(filter_name, current_cte, char_num, value)
            cte_parts.append(filter_cte)
            current_cte = filter_name
            
        return f"WITH {', '.join(cte_parts)} SELECT * FROM {current_cte}"


def main():
    """Demonstrate the query engine capabilities"""
    print("DELTA Taxonomic Query Engine Demo")
    print("=" * 50)
    
    with TaxonomicQueryEngine('delta.db') as engine:
        # Show best discriminating characters
        print("\n1. Best Discriminating Characters:")
        characters = engine.get_character_rankings()
        for i, char in enumerate(characters[:10], 1):
            print(f"{i:2d}. Character {char.number}: {char.description[:60]}...")
            print(f"     Type: {char.character_type}, Distinct values: {char.distinct_values}, "
                  f"Completeness: {char.coding_completeness:.2f}")
        
        # Demonstrate progressive querying
        if characters:
            best_char = characters[0]
            print(f"\n2. Values for Character {best_char.number}:")
            values = engine.get_character_values(best_char.number)
            for value, description, count in values:
                print(f"   {value}: {description} ({count} items)")
            
            # Query by first value
            if values:
                first_value = values[0][0]
                print(f"\n3. Items with Character {best_char.number} = {first_value}:")
                result = engine.query_items_by_character(best_char.number, first_value)
                
                for item in result.matching_items:
                    print(f"   - {item['item_name']}")
                    
                print(f"\n4. Next best characters for refinement:")
                for i, char in enumerate(result.character_candidates[:5], 1):
                    print(f"{i}. Character {char.number}: {char.description[:50]}...")
        
        # Generate sample key
        print(f"\n5. Sample Identification Key:")
        key_steps = engine.generate_identification_key(max_steps=5)
        for i, step in enumerate(key_steps, 1):
            print(f"\nStep {i}: {step.character.description}")
            print(f"   Options:")
            for value, desc, count in step.possible_values[:3]:  # Show first 3 options
                print(f"     {value}: {desc} → {count} items")


if __name__ == "__main__":
    main()