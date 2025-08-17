"""
DELTA format parser using PyParsing
Parses DELTA intkey format files according to https://www.delta-intkey.com/www/standard.htm
"""

import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pyparsing import (
    Word, alphas, nums, alphanums, Literal, Optional as Opt, ZeroOrMore, OneOrMore,
    Suppress, Regex, LineEnd, LineStart, ParseException, QuotedString,
    pyparsing_common, Combine, White, Group, delimitedList
)


@dataclass
class Character:
    number: int
    character_type: str
    feature_description: str
    units: Optional[str] = None
    states: Optional[Dict[int, str]] = None
    implicit_value: Optional[int] = None
    mandatory: bool = False
    comments: Optional[str] = None


@dataclass 
class Item:
    number: int
    name: str
    authority: Optional[str] = None
    comments: Optional[str] = None
    attributes: Dict[int, Any] = None


class DeltaParser:
    def __init__(self):
        self.characters: Dict[int, Character] = {}
        self.items: Dict[int, Item] = {}
        self.dependencies: List[Tuple[int, int, int]] = []  # (parent_char, parent_state, dependent_char)
        self._setup_grammar()
    
    def _setup_grammar(self):
        """Set up PyParsing grammar for DELTA format"""
        
        # Basic tokens
        integer = pyparsing_common.signed_integer()
        real_number = pyparsing_common.real()
        
        # Character number reference
        char_ref = Suppress("#") + integer("char_num")
        
        # State specification: "1. description/"
        state_num = integer + Suppress(".")
        state_desc = Regex(r"[^/\n]+")
        state_spec = Group(state_num("number") + state_desc("description") + Suppress("/"))
        
        # Character specification with states
        char_desc = Regex(r"[^<>/\n]+")
        char_with_states = (char_ref + 
                           char_desc("description") + 
                           Suppress("/") +
                           ZeroOrMore(state_spec)("states"))
        
        # Text in angle brackets for comments/notes
        angle_text = QuotedString("<", endQuoteChar=">")
        
        # Character type specifications from specs file
        char_type_spec = (integer + Suppress(",") + 
                         Word(alphas, exact=2)("type"))
        
        # Character attribute value in items
        # Format: character_number,state_values
        attr_value = (integer("char_num") + 
                     Opt(Suppress(",") + 
                         delimitedList(integer | real_number | angle_text)("values")))
        
        # Item specification 
        # Format: # item_name/
        # followed by attribute values
        item_header = (Suppress("#") + 
                      Regex(r"[^/\n]+")("name") + 
                      Suppress("/"))
        
        item_number = integer("item_num")
        item_spec = (item_header +
                    item_number +
                    ZeroOrMore(attr_value)("attributes"))
        
        # Comments and directives
        comment_line = Regex(r"\*[^\n]*")
        directive = Regex(r"\*[A-Z][^\n]*")
        
        # Store grammar components
        self.char_ref = char_ref
        self.char_with_states = char_with_states
        self.char_type_spec = char_type_spec
        self.item_spec = item_spec
        self.comment_line = comment_line
        self.directive = directive
        self.angle_text = angle_text
        
    def parse_characters_file(self, filepath: str) -> Dict[int, Character]:
        """Parse the characters definition file"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split into lines and process
        lines = content.split('\n')
        current_char = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('*'):
                continue
                
            # Try to parse character definition
            if line.startswith('#'):
                try:
                    # Extract character number and description
                    match = re.match(r'#(\d+)\.\s*(.+)', line)
                    if match:
                        char_num = int(match.group(1))
                        desc = match.group(2).strip()
                        
                        # Handle descriptions in angle brackets specially
                        if desc.startswith('<') and desc.endswith('>'):
                            desc = desc[1:-1]  # Remove outer angle brackets
                        else:
                            # For other cases, keep the full description
                            desc = desc.rstrip('/')
                        
                        current_char = Character(
                            number=char_num,
                            character_type='UM',  # Default, will be updated from specs
                            feature_description=desc,
                            states={}
                        )
                        self.characters[char_num] = current_char
                        
                except (ValueError, AttributeError):
                    continue
                    
            # Parse state definitions
            elif current_char and re.match(r'\s*\d+\.', line):
                try:
                    match = re.match(r'\s*(\d+)\.\s*(.+)', line)
                    if match:
                        state_num = int(match.group(1))
                        state_desc = match.group(2).strip()
                        
                        # Remove angle bracket comments but preserve main description
                        state_desc = re.sub(r'<<[^>]*>>', '', state_desc).strip()  # Remove double angle brackets first
                        state_desc = state_desc.rstrip('/')
                        
                        if current_char.states is None:
                            current_char.states = {}
                        current_char.states[state_num] = state_desc
                        
                except (ValueError, AttributeError):
                    continue
        
        return self.characters
    
    def parse_specs_file(self, filepath: str):
        """Parse the specifications file to get character types and dependencies"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse character types
            if line.startswith('*CHARACTER TYPES'):
                # Extract character type specifications
                type_specs = re.findall(r'(\d+(?:-\d+)?),([A-Z]{2})', line)
                for spec, char_type in type_specs:
                    if '-' in spec:
                        start, end = map(int, spec.split('-'))
                        for i in range(start, end + 1):
                            if i in self.characters:
                                self.characters[i].character_type = char_type
                    else:
                        char_num = int(spec)
                        if char_num in self.characters:
                            self.characters[char_num].character_type = char_type
            
            # Parse implicit values
            elif line.startswith('*IMPLICIT VALUES'):
                impl_specs = re.findall(r'(\d+(?:-\d+)?),(\d+)', line)
                for spec, value in impl_specs:
                    if '-' in spec:
                        start, end = map(int, spec.split('-'))
                        for i in range(start, end + 1):
                            if i in self.characters:
                                self.characters[i].implicit_value = int(value)
                    else:
                        char_num = int(spec)
                        if char_num in self.characters:
                            self.characters[char_num].implicit_value = int(value)
            
            # Parse mandatory characters
            elif line.startswith('*MANDATORY CHARACTERS'):
                mandatory_nums = re.findall(r'\d+', line)
                for num in mandatory_nums:
                    char_num = int(num)
                    if char_num in self.characters:
                        self.characters[char_num].mandatory = True
            
            # Parse dependencies  
            elif line.startswith('*DEPENDENT CHARACTERS'):
                # Format: parent_char,parent_state:dependent_char1:dependent_char2
                dep_specs = re.findall(r'(\d+),(\d+):([0-9:]+)', line)
                for parent_char, parent_state, dependents in dep_specs:
                    parent_char = int(parent_char)
                    parent_state = int(parent_state)
                    for dep_char in dependents.split(':'):
                        if dep_char.isdigit():
                            dep_char = int(dep_char)
                            self.dependencies.append((parent_char, parent_state, dep_char))
    
    def parse_items_file(self, filepath: str) -> Dict[int, Item]:
        """Parse the items file to extract taxon data"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split by item headers (lines starting with #)
        item_blocks = re.split(r'\n(?=#\s)', content)
        
        for block in item_blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            # Parse item header
            header_line = lines[0]
            match = re.match(r'#\s*(.+?)/', header_line)
            if not match:
                continue
                
            item_name = match.group(1).strip()
            
            # Look for item number in subsequent lines
            item_number = None
            attributes = {}
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                # Try to find item number (usually first numeric value)
                if item_number is None:
                    num_match = re.search(r'\b(\d+)(?:<|,|\s)', line)
                    if num_match:
                        item_number = int(num_match.group(1))
                
                # Parse character attributes (format: char_num,values or char_num<text>)
                # Handle both formats: "31,5" and "31<text>"
                attr_matches = re.findall(r'(\d+)(?:,([^,\s<]+)|<([^>]*)>)', line)
                for match in attr_matches:
                    char_num = int(match[0])
                    value_str = match[1] if match[1] else match[2]
                    if not value_str:
                        continue
                    
                    # Handle special pseudo-values
                    if value_str in ['U', 'V', '-']:
                        attributes[char_num] = {'pseudo_value': value_str}
                    # Handle range values (e.g., "8.5-14", "10-15") but not dates like "1930.6.3.603"
                    elif re.match(r'^[\d.]{1,10}\s*-\s*[\d.]{1,10}$', value_str) and value_str.count('.') <= 2:
                        parts = value_str.split('-')
                        try:
                            min_val = float(parts[0].strip()) if '.' in parts[0] else int(parts[0].strip())
                            max_val = float(parts[1].strip()) if '.' in parts[1] else int(parts[1].strip())
                            attributes[char_num] = {'range': [min_val, max_val]}
                        except ValueError:
                            # If conversion fails, treat as text
                            attributes[char_num] = value_str
                    # Parse different value types
                    elif value_str.isdigit():
                        attributes[char_num] = int(value_str)
                    elif re.match(r'^\d+\.\d+$', value_str):
                        attributes[char_num] = float(value_str)
                    # Handle multistate values (e.g., "1&3&5")
                    elif '&' in value_str:
                        states = [int(s) for s in value_str.split('&') if s.isdigit()]
                        attributes[char_num] = {'states': states}
                    else:
                        # Text or other complex value
                        attributes[char_num] = value_str
            
            if item_number is not None:
                item = Item(
                    number=item_number,
                    name=item_name,
                    attributes=attributes
                )
                self.items[item_number] = item
        
        return self.items
    
    def create_database(self, db_path: str):
        """Create SQLite database and populate with parsed data"""
        # Read schema
        schema_path = Path(__file__).parent / 'schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Create database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute schema
        cursor.executescript(schema_sql)
        
        # Insert characters
        for char in self.characters.values():
            cursor.execute("""
                INSERT INTO characters 
                (character_number, character_type, feature_description, units, 
                 min_states, max_states, implicit_value, mandatory, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                char.number, char.character_type, char.feature_description,
                char.units, 
                1 if char.states else None,
                len(char.states) if char.states else None,
                char.implicit_value, char.mandatory, char.comments
            ))
            
            char_id = cursor.lastrowid
            
            # Insert character states
            if char.states:
                for state_num, state_desc in char.states.items():
                    cursor.execute("""
                        INSERT INTO character_states 
                        (character_id, state_number, state_description)
                        VALUES (?, ?, ?)
                    """, (char_id, state_num, state_desc))
        
        # Insert dependencies
        for parent_char, parent_state, dep_char in self.dependencies:
            cursor.execute("""
                INSERT INTO character_dependencies 
                (parent_character_id, parent_state, dependent_character_id)
                SELECT p.id, ?, d.id
                FROM characters p, characters d
                WHERE p.character_number = ? AND d.character_number = ?
            """, (parent_state, parent_char, dep_char))
        
        # Insert items
        for item in self.items.values():
            cursor.execute("""
                INSERT INTO items (item_number, item_name, authority, comments)
                VALUES (?, ?, ?, ?)
            """, (item.number, item.name, item.authority, item.comments))
            
            item_id = cursor.lastrowid
            
            # Insert item attributes
            if item.attributes:
                for char_num, value in item.attributes.items():
                    # Handle different value types
                    integer_val = None
                    real_val = None
                    text_val = None
                    state_vals = None
                    range_min = None
                    range_max = None
                    is_variable = False
                    is_unknown = False
                    is_not_applicable = False
                    
                    if isinstance(value, dict):
                        if 'pseudo_value' in value:
                            pseudo = value['pseudo_value']
                            is_variable = (pseudo == 'V')
                            is_unknown = (pseudo == 'U')
                            is_not_applicable = (pseudo == '-')
                        elif 'range' in value:
                            range_min, range_max = value['range']
                        elif 'states' in value:
                            state_vals = json.dumps(value['states'])
                    elif isinstance(value, int):
                        integer_val = value
                    elif isinstance(value, float):
                        real_val = value
                    elif isinstance(value, str):
                        text_val = value
                    
                    cursor.execute("""
                        INSERT INTO item_character_attributes 
                        (item_id, character_id, integer_value, real_value, text_value, 
                         state_values, range_min, range_max, is_variable, is_unknown, is_not_applicable)
                        SELECT ?, c.id, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        FROM characters c WHERE c.character_number = ?
                    """, (
                        item_id, integer_val, real_val, text_val, state_vals,
                        range_min, range_max, is_variable, is_unknown, is_not_applicable,
                        char_num
                    ))
        
        conn.commit()
        conn.close()
        
        return db_path


def main():
    """Main function to parse DELTA files and create database"""
    parser = DeltaParser()
    
    # Parse files
    data_dir = Path('data')
    
    print("Parsing characters file...")
    parser.parse_characters_file(str(data_dir / 'chars'))
    
    print("Parsing specs file...")
    parser.parse_specs_file(str(data_dir / 'specs'))
    
    print("Parsing items file...")
    parser.parse_items_file(str(data_dir / 'items'))
    
    print(f"Parsed {len(parser.characters)} characters and {len(parser.items)} items")
    
    # Create database
    print("Creating database...")
    db_path = parser.create_database('delta.db')
    print(f"Database created at {db_path}")


if __name__ == "__main__":
    main()