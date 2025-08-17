#!/usr/bin/env python3
"""
Interactive Taxonomic Identification Key

This module provides an interactive command-line interface for using
the DELTA query engine to identify specimens step by step.
"""

import sys
from typing import List, Tuple, Any, Optional
from query_engine import TaxonomicQueryEngine, CharacterInfo


class InteractiveKey:
    """Interactive taxonomic identification key interface"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.history: List[Tuple[int, Any, str]] = []  # (char_num, value, description)
        self.current_items: List[dict] = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def start_identification(self):
        """Start the interactive identification process"""
        print("🔬 DELTA Interactive Taxonomic Key")
        print("=" * 50)
        
        # Get initial item count
        with TaxonomicQueryEngine(self.db_path) as engine:
            cursor = engine.conn.execute("SELECT COUNT(*) as count FROM items")
            total_items = cursor.fetchone()['count']
            
        print(f"Starting with {total_items} taxa in the database.")
        print("Answer each question to narrow down the identification.")
        print("Type 'help' for commands, 'back' to undo, 'quit' to exit.\n")
        
        while True:
            try:
                if not self._identification_step():
                    break
            except KeyboardInterrupt:
                print("\n\nExiting identification key...")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue
                
        print("Thank you for using the DELTA identification key!")
    
    def _identification_step(self) -> bool:
        """
        Perform one step of the identification process
        Returns False if identification is complete or user wants to quit
        """
        with TaxonomicQueryEngine(self.db_path) as engine:
            # Get current state
            if self.history:
                # Apply all previous filters
                filters = [(char_num, value) for char_num, value, _ in self.history]
                if len(filters) == 1:
                    result = engine.query_items_by_character(filters[0][0], filters[0][1])
                else:
                    result = engine.query_items_by_character(
                        filters[-1][0], filters[-1][1], filters[:-1]
                    )
                self.current_items = result.matching_items
                candidates = result.character_candidates
            else:
                # First step
                cursor = engine.conn.execute("SELECT id, item_name, item_number FROM items")
                self.current_items = [dict(row) for row in cursor.fetchall()]
                candidates = engine.get_character_rankings()
            
            # Check if identification is complete
            if len(self.current_items) == 0:
                print("❌ No taxa match your selections. Please check your answers.")
                print("Type 'back' to undo the last selection or 'restart' to start over.")
                command = input("Command: ").strip().lower()
                return self._handle_command(command)
                
            elif len(self.current_items) == 1:
                item = self.current_items[0]
                print(f"✅ Identification complete!")
                print(f"🎯 Result: {item['item_name']}")
                print(f"\nIdentification path:")
                for i, (char_num, value, desc) in enumerate(self.history, 1):
                    print(f"  {i}. Character {char_num}: {desc}")
                return False
                
            # Show current status
            print(f"\n📊 Current status: {len(self.current_items)} taxa remaining")
            if len(self.current_items) <= 5:
                print("Remaining taxa:")
                for item in self.current_items:
                    print(f"  • {item['item_name']}")
            
            # Show identification path so far
            if self.history:
                print(f"\n📝 Your selections:")
                for i, (char_num, value, desc) in enumerate(self.history, 1):
                    print(f"  {i}. {desc}")
            
            # Show next best characters
            if not candidates:
                print("\n⚠️  No more discriminating characters available.")
                print("Remaining taxa cannot be distinguished with available data.")
                return False
                
            print(f"\n🔍 Next character to examine:")
            best_char = candidates[0]
            print(f"Character {best_char.number}: {best_char.description}")
            print(f"Type: {best_char.character_type}")
            
            # Get possible values
            item_numbers = [item['item_number'] for item in self.current_items]
            possible_values = engine.get_character_values(best_char.number, item_numbers)
            
            if not possible_values:
                print("⚠️  No coded values available for this character.")
                return True
                
            # Show options
            print("\nPossible values:")
            for i, (value, description, count) in enumerate(possible_values, 1):
                # Clean up description for display
                clean_desc = description.replace('\\i{}', '').replace('\\i0{}', '')
                clean_desc = clean_desc.replace('\\b{}', '').replace('\\b0{}', '')
                if len(clean_desc) > 60:
                    clean_desc = clean_desc[:57] + "..."
                print(f"  {i}. {clean_desc} ({count} taxa)")
            
            # Get user input
            print(f"\nSelect an option (1-{len(possible_values)}):")
            user_input = input("Choice (or 'help', 'back', 'restart', 'quit'): ").strip()
            
            # Handle commands
            if user_input.lower() in ['help', 'back', 'restart', 'quit']:
                return self._handle_command(user_input.lower())
            
            # Parse selection
            try:
                choice = int(user_input)
                if 1 <= choice <= len(possible_values):
                    selected_value, selected_desc, _ = possible_values[choice - 1]
                    
                    # Clean description for history
                    clean_desc = selected_desc.replace('\\i{}', '').replace('\\i0{}', '')
                    clean_desc = clean_desc.replace('\\b{}', '').replace('\\b0{}', '')
                    
                    # Add to history
                    history_desc = f"Character {best_char.number} = {clean_desc}"
                    self.history.append((best_char.number, selected_value, history_desc))
                    
                    print(f"✓ Selected: {clean_desc}")
                    return True
                else:
                    print(f"Please enter a number between 1 and {len(possible_values)}")
                    return True
                    
            except ValueError:
                print("Please enter a valid number or command")
                return True
    
    def _handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True to continue, False to quit"""
        if command == 'help':
            print("\n📖 Available commands:")
            print("  help     - Show this help message")
            print("  back     - Undo the last selection")
            print("  restart  - Start the identification over")
            print("  quit     - Exit the identification key")
            print("  1-N      - Select an option by number")
            return True
            
        elif command == 'back':
            if self.history:
                removed = self.history.pop()
                print(f"↶ Undid: {removed[2]}")
            else:
                print("Nothing to undo - you're at the beginning")
            return True
            
        elif command == 'restart':
            self.history.clear()
            self.current_items.clear()
            print("🔄 Restarting identification...")
            return True
            
        elif command == 'quit':
            return False
            
        else:
            print(f"Unknown command: {command}")
            return True
    
    def show_statistics(self):
        """Show statistics about the database and characters"""
        with TaxonomicQueryEngine(self.db_path) as engine:
            print("\n📈 Database Statistics:")
            
            # Total counts
            cursor = engine.conn.execute("SELECT COUNT(*) FROM characters")
            char_count = cursor.fetchone()[0]
            
            cursor = engine.conn.execute("SELECT COUNT(*) FROM items") 
            item_count = cursor.fetchone()[0]
            
            cursor = engine.conn.execute("SELECT COUNT(*) FROM character_states")
            state_count = cursor.fetchone()[0]
            
            print(f"  Characters: {char_count}")
            print(f"  Taxa: {item_count}")  
            print(f"  Character states: {state_count}")
            
            # Character type breakdown
            cursor = engine.conn.execute("""
                SELECT character_type, COUNT(*) as count 
                FROM characters 
                GROUP BY character_type 
                ORDER BY count DESC
            """)
            print(f"\n  Character types:")
            for row in cursor:
                type_name = {
                    'TE': 'Text',
                    'IN': 'Integer',
                    'RN': 'Real number', 
                    'UM': 'Unordered multistate',
                    'OM': 'Ordered multistate'
                }.get(row[0], row[0])
                print(f"    {type_name}: {row[1]}")
            
            # Best discriminating characters
            print(f"\n  Top 5 discriminating characters:")
            characters = engine.get_character_rankings()
            for i, char in enumerate(characters[:5], 1):
                desc = char.description.replace('<', '').replace('>', '')
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                print(f"    {i}. {desc}")
                print(f"       (Type: {char.character_type}, "
                      f"Distinct values: {char.distinct_values})")


def main():
    """Main entry point for the interactive key"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("DELTA Interactive Taxonomic Key")
        print("Usage: python3 interactive_key.py [database.db]")
        print("\nCommands during identification:")
        print("  help     - Show help")
        print("  back     - Undo last selection") 
        print("  restart  - Start over")
        print("  quit     - Exit")
        return
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'delta.db'
    
    try:
        with InteractiveKey(db_path) as key:
            # Show statistics first
            key.show_statistics()
            
            print("\nReady to start identification!")
            input("Press Enter to begin...")
            
            # Start identification
            key.start_identification()
            
    except FileNotFoundError:
        print(f"Error: Database file '{db_path}' not found.")
        print("Run 'python3 delta_parser.py' first to create the database.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()