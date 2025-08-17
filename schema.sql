-- SQLite schema for DELTA intkey format
-- Based on https://www.delta-intkey.com/www/standard.htm

-- Table to store character definitions
CREATE TABLE characters (
    id INTEGER PRIMARY KEY,
    character_number INTEGER NOT NULL UNIQUE,
    character_type TEXT NOT NULL CHECK (character_type IN ('TE', 'IN', 'RN', 'UM', 'OM')),
    feature_description TEXT NOT NULL,
    units TEXT,
    min_states INTEGER,
    max_states INTEGER,
    implicit_value INTEGER,
    mandatory BOOLEAN DEFAULT FALSE,
    omit_from_key BOOLEAN DEFAULT FALSE, -- For characters marked as OMIT
    use_controlling_characters_first BOOLEAN DEFAULT FALSE, -- For key generation optimization
    comments TEXT
);

-- Table to store character states for multistate characters
CREATE TABLE character_states (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    state_number INTEGER NOT NULL,
    state_description TEXT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES characters(id),
    UNIQUE(character_id, state_number)
);

-- Table to store character dependencies 
CREATE TABLE character_dependencies (
    id INTEGER PRIMARY KEY,
    parent_character_id INTEGER NOT NULL,
    parent_state INTEGER NOT NULL,
    dependent_character_id INTEGER NOT NULL,
    FOREIGN KEY (parent_character_id) REFERENCES characters(id),
    FOREIGN KEY (dependent_character_id) REFERENCES characters(id)
);

-- Table to store taxon/item definitions
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    item_number INTEGER NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    authority TEXT,
    comments TEXT
);

-- Table to store character attribute values for each item
CREATE TABLE item_character_attributes (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    
    -- Value storage for different data types
    integer_value INTEGER,
    real_value REAL, 
    text_value TEXT,
    state_values TEXT, -- JSON array for multistate values like "[1,3,5]"
    
    -- Range and alternative values
    range_min REAL,
    range_max REAL,
    alternative_values TEXT, -- JSON array for alternative values
    
    -- Special pseudo-values
    is_variable BOOLEAN DEFAULT FALSE,     -- 'V' variable
    is_unknown BOOLEAN DEFAULT FALSE,      -- 'U' unknown  
    is_not_applicable BOOLEAN DEFAULT FALSE, -- '-' not applicable
    
    -- Comments and modifiers
    comments TEXT,
    
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (character_id) REFERENCES characters(id),
    UNIQUE(item_id, character_id)
);

-- Indexes for performance
CREATE INDEX idx_characters_number ON characters(character_number);
CREATE INDEX idx_character_states_char_id ON character_states(character_id);
CREATE INDEX idx_item_attributes_item ON item_character_attributes(item_id);
CREATE INDEX idx_item_attributes_char ON item_character_attributes(character_id);
CREATE INDEX idx_dependencies_parent ON character_dependencies(parent_character_id);
CREATE INDEX idx_dependencies_dependent ON character_dependencies(dependent_character_id);

-- View to simplify character querying with state information
CREATE VIEW character_details AS
SELECT 
    c.character_number,
    c.character_type,
    c.feature_description,
    c.units,
    c.mandatory,
    c.implicit_value,
    COUNT(cs.id) as state_count,
    c.comments
FROM characters c
LEFT JOIN character_states cs ON c.id = cs.character_id
GROUP BY c.id, c.character_number, c.character_type, c.feature_description, c.units, c.mandatory, c.implicit_value, c.comments;

-- View for item character matrix (like a traditional morphological matrix)
CREATE VIEW character_matrix AS
SELECT 
    i.item_name,
    c.character_number,
    c.feature_description,
    CASE 
        WHEN ica.is_not_applicable THEN '-'
        WHEN ica.is_unknown THEN 'U' 
        WHEN ica.is_variable THEN 'V'
        WHEN c.character_type = 'TE' THEN ica.text_value
        WHEN c.character_type = 'IN' THEN CAST(ica.integer_value AS TEXT)
        WHEN c.character_type = 'RN' THEN CAST(ica.real_value AS TEXT)
        WHEN c.character_type IN ('UM', 'OM') THEN ica.state_values
        ELSE NULL
    END as character_value,
    ica.comments
FROM items i
CROSS JOIN characters c
LEFT JOIN item_character_attributes ica ON i.id = ica.item_id AND c.id = ica.character_id
ORDER BY i.item_number, c.character_number;

-- Additional view for key generation - shows best characters for discriminating items
CREATE VIEW key_characters AS
SELECT 
    c.character_number,
    c.feature_description,
    c.character_type,
    COUNT(DISTINCT ica.state_values || ica.integer_value || ica.real_value || ica.text_value) as distinct_values,
    COUNT(ica.id) as coded_items,
    CAST(COUNT(ica.id) AS REAL) / (SELECT COUNT(*) FROM items) as coding_completeness
FROM characters c
LEFT JOIN item_character_attributes ica ON c.id = ica.character_id
WHERE c.omit_from_key = FALSE 
    AND c.mandatory = FALSE
    AND NOT (ica.is_unknown OR ica.is_variable OR ica.is_not_applicable)
GROUP BY c.id, c.character_number, c.feature_description, c.character_type
HAVING coding_completeness > 0.5  -- Only include characters coded for more than 50% of items
ORDER BY distinct_values DESC, coding_completeness DESC;