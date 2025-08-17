#!/usr/bin/env python3
"""
DELTA CLI - Command Line Interface for Taxonomic Key Operations

This CLI supports:
- Proposing the most selective character given a preexisting set of characters
- Building up a set of filters by appending additional clauses
- Filter state management and programmatic access
"""

import argparse
import json
import sys
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from query_engine import TaxonomicQueryEngine, CharacterInfo


class FilterState:
    """Manages the current state of filters for building taxonomic keys"""
    
    def __init__(self):
        self.filters: List[Tuple[int, Any, str]] = []  # (char_num, value, description)
        self.current_items: List[Dict[str, Any]] = []
        self.available_characters: List[CharacterInfo] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter state to dictionary for JSON serialization"""
        return {
            'filters': [
                {
                    'character_number': char_num,
                    'value': value,
                    'description': desc
                }
                for char_num, value, desc in self.filters
            ],
            'current_items': self.current_items,
            'remaining_count': len(self.current_items),
            'available_characters': [
                {
                    'number': char.number,
                    'description': char.description,
                    'type': char.character_type,
                    'distinct_values': char.distinct_values,
                    'selectivity_score': char.selectivity_score
                }
                for char in self.available_characters
            ]
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load filter state from dictionary"""
        self.filters = [
            (f['character_number'], f['value'], f['description'])
            for f in data.get('filters', [])
        ]
        self.current_items = data.get('current_items', [])
        # available_characters would need to be recalculated from engine
    
    def add_filter(self, char_num: int, value: Any, description: str):
        """Add a new filter to the state"""
        self.filters.append((char_num, value, description))
    
    def remove_last_filter(self) -> Optional[Tuple[int, Any, str]]:
        """Remove and return the last filter"""
        if self.filters:
            return self.filters.pop()
        return None
    
    def clear_filters(self):
        """Clear all filters"""
        self.filters.clear()
        self.current_items.clear()
        self.available_characters.clear()


class DeltaCLI:
    """Command Line Interface for DELTA taxonomic operations"""
    
    def __init__(self, db_path: str, state_file: str = '.delta_cli_state.json'):
        self.db_path = db_path
        self.state_file = state_file
        self.filter_state = FilterState()
        self._load_state()
    
    def _load_state(self):
        """Load filter state from file if it exists"""
        state_path = Path(self.state_file)
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    data = json.load(f)
                self.filter_state.from_dict(data)
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                # If state file is corrupted, start fresh
                pass
    
    def _save_state(self):
        """Save current filter state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.filter_state.to_dict(), f, indent=2)
        except (IOError, OSError):
            # If we can't save state, continue without persistence
            pass
        
    def propose_character(self, exclude_chars: List[int] = None, 
                         output_format: str = 'text') -> Dict[str, Any]:
        """
        Propose the most selective character given existing filters
        
        Args:
            exclude_chars: List of character numbers to exclude
            output_format: 'text' or 'json'
            
        Returns:
            Dictionary with proposed character information
        """
        with TaxonomicQueryEngine(self.db_path) as engine:
            # Get current state
            if self.filter_state.filters:
                # Apply existing filters to get current items
                filters = [(char_num, value) for char_num, value, _ in self.filter_state.filters]
                if len(filters) == 1:
                    result = engine.query_items_by_character(filters[0][0], filters[0][1])
                else:
                    result = engine.query_items_by_character(
                        filters[-1][0], filters[-1][1], filters[:-1]
                    )
                self.filter_state.current_items = result.matching_items
                candidates = result.character_candidates
            else:
                # No filters yet - get all items and best characters
                cursor = engine.conn.execute("SELECT id, item_name, item_number FROM items")
                self.filter_state.current_items = [dict(row) for row in cursor.fetchall()]
                candidates = engine.get_character_rankings()
            
            # Apply exclusions
            if exclude_chars:
                exclude_set = set(exclude_chars)
                candidates = [c for c in candidates if c.number not in exclude_set]
            
            # Update available characters
            self.filter_state.available_characters = candidates
            
            # Get the best character
            if not candidates:
                return {
                    'status': 'no_candidates',
                    'message': 'No suitable characters available for discrimination',
                    'remaining_items': len(self.filter_state.current_items)
                }
            
            best_char = candidates[0]
            
            # Get possible values for this character
            item_numbers = [item['item_number'] for item in self.filter_state.current_items]
            possible_values = engine.get_character_values(best_char.number, item_numbers)
            
            result = {
                'status': 'success',
                'character': {
                    'number': best_char.number,
                    'description': best_char.description,
                    'type': best_char.character_type,
                    'distinct_values': best_char.distinct_values,
                    'selectivity_score': best_char.selectivity_score
                },
                'possible_values': [
                    {
                        'value': value,
                        'description': desc,
                        'item_count': count
                    }
                    for value, desc, count in possible_values
                ],
                'remaining_items': len(self.filter_state.current_items),
                'current_filters': len(self.filter_state.filters)
            }
            
            if output_format == 'json':
                return result
            else:
                # Format for text output
                self._print_character_proposal(result)
                return result
    
    def _print_character_proposal(self, result: Dict[str, Any]):
        """Print character proposal in human-readable format"""
        if result['status'] != 'success':
            print(f"❌ {result['message']}")
            return
            
        char = result['character']
        print(f"🎯 Most selective character:")
        print(f"   Character {char['number']}: {char['description']}")
        print(f"   Type: {char['type']}")
        print(f"   Selectivity score: {char['selectivity_score']:.2f}")
        print(f"   Distinct values: {char['distinct_values']}")
        print(f"   Remaining items: {result['remaining_items']}")
        
        if result['possible_values']:
            print(f"\n   Possible values:")
            for i, val in enumerate(result['possible_values'][:10], 1):  # Show max 10
                desc = val['description']
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                print(f"     {i}. {desc} ({val['item_count']} items)")
            
            if len(result['possible_values']) > 10:
                print(f"     ... and {len(result['possible_values']) - 10} more values")
    
    def add_filter(self, char_num: int, value: Any, 
                   output_format: str = 'text') -> Dict[str, Any]:
        """
        Add a filter clause to the current filter set
        
        Args:
            char_num: Character number to filter on
            value: Value to filter by
            output_format: 'text' or 'json'
            
        Returns:
            Dictionary with updated filter state
        """
        with TaxonomicQueryEngine(self.db_path) as engine:
            # Get character info for description
            char_info = engine.get_character_info(char_num)
            if not char_info:
                result = {
                    'status': 'error',
                    'message': f'Character {char_num} not found'
                }
                if output_format == 'text':
                    print(f"❌ {result['message']}")
                return result
            
            # Build description for the filter
            desc = f"Character {char_num} = {value}"
            
            # Add to filter state
            self.filter_state.add_filter(char_num, value, desc)
            
            # Apply all filters to get new state
            try:
                filters = [(cn, v) for cn, v, _ in self.filter_state.filters]
                if len(filters) == 1:
                    query_result = engine.query_items_by_character(filters[0][0], filters[0][1])
                else:
                    query_result = engine.query_items_by_character(
                        filters[-1][0], filters[-1][1], filters[:-1]
                    )
                
                self.filter_state.current_items = query_result.matching_items
                self.filter_state.available_characters = query_result.character_candidates
                
                result = {
                    'status': 'success',
                    'message': f'Added filter: {desc}',
                    'remaining_items': len(self.filter_state.current_items),
                    'total_filters': len(self.filter_state.filters),
                    'items': [item['item_name'] for item in self.filter_state.current_items]
                }
                
                if output_format == 'text':
                    self._print_filter_result(result)
                
                # Save state after successful filter addition
                self._save_state()
                return result
                
            except Exception as e:
                # Remove the failed filter
                self.filter_state.remove_last_filter()
                result = {
                    'status': 'error',
                    'message': f'Failed to apply filter: {str(e)}'
                }
                if output_format == 'text':
                    print(f"❌ {result['message']}")
                return result
    
    def _print_filter_result(self, result: Dict[str, Any]):
        """Print filter result in human-readable format"""
        if result['status'] != 'success':
            print(f"❌ {result['message']}")
            return
            
        print(f"✅ {result['message']}")
        print(f"   Remaining items: {result['remaining_items']}")
        print(f"   Total filters: {result['total_filters']}")
        
        if result['remaining_items'] <= 5:
            print(f"   Items:")
            for item in result['items']:
                clean_name = item.replace('\\i{}', '').replace('\\i0{}', '')
                print(f"     • {clean_name}")
    
    def show_state(self, output_format: str = 'text') -> Dict[str, Any]:
        """Show current filter state"""
        state_dict = self.filter_state.to_dict()
        
        # Add status field for consistency
        state_dict['status'] = 'success'
        
        if output_format == 'json':
            return state_dict
        else:
            self._print_state(state_dict)
            return state_dict
    
    def _print_state(self, state: Dict[str, Any]):
        """Print current state in human-readable format"""
        print(f"📊 Current Filter State:")
        print(f"   Filters applied: {len(state['filters'])}")
        print(f"   Remaining items: {state['remaining_count']}")
        
        if state['filters']:
            print(f"   Active filters:")
            for i, f in enumerate(state['filters'], 1):
                print(f"     {i}. {f['description']}")
        
        if state['remaining_count'] <= 5 and state['current_items']:
            print(f"   Remaining items:")
            for item in state['current_items']:
                clean_name = item['item_name'].replace('\\i{}', '').replace('\\i0{}', '')
                print(f"     • {clean_name}")
        
        if state['available_characters']:
            print(f"   Next best characters:")
            for i, char in enumerate(state['available_characters'][:3], 1):
                desc = char['description']
                if len(desc) > 40:
                    desc = desc[:37] + "..."
                print(f"     {i}. Character {char['number']}: {desc}")
    
    def reset_filters(self, output_format: str = 'text') -> Dict[str, Any]:
        """Reset all filters"""
        self.filter_state.clear_filters()
        
        result = {
            'status': 'success',
            'message': 'All filters cleared'
        }
        
        if output_format == 'text':
            print(f"🔄 {result['message']}")
        
        # Save state after reset
        self._save_state()
        return result
    
    def undo_last_filter(self, output_format: str = 'text') -> Dict[str, Any]:
        """Remove the last applied filter"""
        removed = self.filter_state.remove_last_filter()
        
        if not removed:
            result = {
                'status': 'error',
                'message': 'No filters to remove'
            }
            if output_format == 'text':
                print(f"⚠️  {result['message']}")
            return result
        
        # Recalculate state with remaining filters
        if self.filter_state.filters:
            with TaxonomicQueryEngine(self.db_path) as engine:
                filters = [(cn, v) for cn, v, _ in self.filter_state.filters]
                if len(filters) == 1:
                    query_result = engine.query_items_by_character(filters[0][0], filters[0][1])
                else:
                    query_result = engine.query_items_by_character(
                        filters[-1][0], filters[-1][1], filters[:-1]
                    )
                self.filter_state.current_items = query_result.matching_items
                self.filter_state.available_characters = query_result.character_candidates
        else:
            # No filters left - reset to all items
            with TaxonomicQueryEngine(self.db_path) as engine:
                cursor = engine.conn.execute("SELECT id, item_name, item_number FROM items")
                self.filter_state.current_items = [dict(row) for row in cursor.fetchall()]
                self.filter_state.available_characters = engine.get_character_rankings()
        
        result = {
            'status': 'success',
            'message': f'Removed filter: {removed[2]}',
            'remaining_items': len(self.filter_state.current_items)
        }
        
        if output_format == 'text':
            print(f"↶ {result['message']}")
            print(f"   Remaining items: {result['remaining_items']}")
        
        # Save state after undo
        self._save_state()
        return result


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description='DELTA CLI - Taxonomic Key Operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Propose the most selective character
  python3 delta_cli.py propose
  
  # Add a filter and see results
  python3 delta_cli.py add-filter 46 2
  
  # Chain operations: add filter, then propose next character
  python3 delta_cli.py add-filter 46 2 && python3 delta_cli.py propose
  
  # Show current state
  python3 delta_cli.py state
  
  # Reset all filters
  python3 delta_cli.py reset
  
  # JSON output for programmatic use
  python3 delta_cli.py propose --json
        """
    )
    
    parser.add_argument('--db', default='delta.db',
                       help='Path to DELTA database (default: delta.db)')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON instead of human-readable text')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Propose character command
    propose_parser = subparsers.add_parser('propose', 
                                          help='Propose most selective character')
    propose_parser.add_argument('--exclude', type=int, nargs='*',
                               help='Character numbers to exclude')
    
    # Add filter command  
    filter_parser = subparsers.add_parser('add-filter',
                                         help='Add a filter clause')
    filter_parser.add_argument('character', type=int,
                              help='Character number to filter on')
    filter_parser.add_argument('value',
                              help='Value to filter by')
    
    # State command
    subparsers.add_parser('state', help='Show current filter state')
    
    # Reset command
    subparsers.add_parser('reset', help='Reset all filters')
    
    # Undo command
    subparsers.add_parser('undo', help='Remove last filter')
    
    return parser


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Check database exists
    if not Path(args.db).exists():
        print(f"❌ Database file '{args.db}' not found.")
        print("Run 'python3 delta_parser.py' first to create the database.")
        sys.exit(1)
    
    cli = DeltaCLI(args.db)
    output_format = 'json' if args.json else 'text'
    
    try:
        if args.command == 'propose':
            result = cli.propose_character(
                exclude_chars=args.exclude or [],
                output_format=output_format
            )
            
        elif args.command == 'add-filter':
            # Parse value - try int, float, then string
            value = args.value
            try:
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass  # Keep as string
                
            result = cli.add_filter(
                char_num=args.character,
                value=value,
                output_format=output_format
            )
            
        elif args.command == 'state':
            result = cli.show_state(output_format=output_format)
            
        elif args.command == 'reset':
            result = cli.reset_filters(output_format=output_format)
            
        elif args.command == 'undo':
            result = cli.undo_last_filter(output_format=output_format)
            
        else:
            parser.print_help()
            return
        
        # Output JSON if requested
        if args.json:
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        if args.json:
            print(json.dumps({
                'status': 'error',
                'message': str(e)
            }))
        else:
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()