#!/usr/bin/env python3
"""
Flask API for DELTA Web Interface

This API provides endpoints for the React frontend to interact with
the DELTA database using the same query engine logic.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from query_engine import TaxonomicQueryEngine
from delta_cli import DeltaCLI, FilterState

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Global state management (in production, use Redis or database)
sessions = {}

def get_session(session_id='default'):
    """Get or create a session for filter state management"""
    if session_id not in sessions:
        sessions[session_id] = {
            'cli': DeltaCLI('delta.db', f'.delta_session_{session_id}.json'),
            'filters': []
        }
    return sessions[session_id]

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'DELTA API is running'})

@app.route('/api/database/stats', methods=['GET'])
def database_stats():
    """Get database statistics"""
    try:
        with TaxonomicQueryEngine('delta.db') as engine:
            # Get character count
            cursor = engine.conn.execute("SELECT COUNT(*) as count FROM characters")
            char_count = cursor.fetchone()['count']
            
            # Get item count
            cursor = engine.conn.execute("SELECT COUNT(*) as count FROM items")
            item_count = cursor.fetchone()['count']
            
            # Get character type breakdown
            cursor = engine.conn.execute("""
                SELECT character_type, COUNT(*) as count 
                FROM characters 
                GROUP BY character_type 
                ORDER BY count DESC
            """)
            char_types = {row['character_type']: row['count'] for row in cursor}
            
            return jsonify({
                'status': 'success',
                'characters': char_count,
                'items': item_count,
                'character_types': char_types
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/propose', methods=['GET'])
def propose_character():
    """Propose the most selective character"""
    session_id = request.args.get('session', 'default')
    exclude_chars = request.args.getlist('exclude', type=int)
    
    try:
        session = get_session(session_id)
        result = session['cli'].propose_character(
            exclude_chars=exclude_chars,
            output_format='json'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/filter', methods=['POST'])
def add_filter():
    """Add a filter clause"""
    session_id = request.json.get('session', 'default')
    char_num = request.json.get('character_number')
    value = request.json.get('value')
    
    if char_num is None or value is None:
        return jsonify({
            'status': 'error', 
            'message': 'character_number and value are required'
        }), 400
    
    try:
        session = get_session(session_id)
        result = session['cli'].add_filter(
            char_num=char_num,
            value=value,
            output_format='json'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current filter state"""
    session_id = request.args.get('session', 'default')
    
    try:
        session = get_session(session_id)
        result = session['cli'].show_state(output_format='json')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/state', methods=['DELETE'])
def reset_state():
    """Reset all filters"""
    session_id = request.args.get('session', 'default')
    
    try:
        session = get_session(session_id)
        result = session['cli'].reset_filters(output_format='json')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/undo', methods=['POST'])
def undo_filter():
    """Remove the last filter"""
    session_id = request.json.get('session', 'default')
    
    try:
        session = get_session(session_id)
        result = session['cli'].undo_last_filter(output_format='json')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/character/<int:char_num>/values', methods=['GET'])
def get_character_values(char_num):
    """Get possible values for a character"""
    session_id = request.args.get('session', 'default')
    
    try:
        session = get_session(session_id)
        
        # Get current items to filter values
        state = session['cli'].show_state(output_format='json')
        item_numbers = None
        if state['current_items']:
            item_numbers = [item['item_number'] for item in state['current_items']]
        
        with TaxonomicQueryEngine('delta.db') as engine:
            values = engine.get_character_values(char_num, item_numbers)
            
            return jsonify({
                'status': 'success',
                'character_number': char_num,
                'values': [
                    {
                        'value': value,
                        'description': desc,
                        'item_count': count
                    }
                    for value, desc, count in values
                ]
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/character/<int:char_num>/info', methods=['GET'])
def get_character_info(char_num):
    """Get detailed character information"""
    try:
        with TaxonomicQueryEngine('delta.db') as engine:
            char_info = engine.get_character_info(char_num)
            
            if not char_info:
                return jsonify({
                    'status': 'error',
                    'message': f'Character {char_num} not found'
                }), 404
            
            return jsonify({
                'status': 'success',
                'character': {
                    'number': char_info.number,
                    'description': char_info.description,
                    'type': char_info.character_type,
                    'states': char_info.states
                }
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all items or filtered items"""
    session_id = request.args.get('session', 'default')
    
    try:
        session = get_session(session_id)
        state = session['cli'].show_state(output_format='json')
        
        return jsonify({
            'status': 'success',
            'items': state['current_items'],
            'total_count': state['remaining_count']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/workflow/auto', methods=['POST'])
def auto_workflow():
    """Automatically build an identification key"""
    session_id = request.json.get('session', 'default')
    max_steps = request.json.get('max_steps', 10)
    
    try:
        session = get_session(session_id)
        
        # Reset first
        session['cli'].reset_filters(output_format='json')
        
        steps = []
        for step in range(max_steps):
            # Get proposal
            proposal = session['cli'].propose_character(output_format='json')
            
            if proposal['status'] != 'success':
                break
            
            char_num = proposal['character']['number']
            possible_values = proposal['possible_values']
            
            if not possible_values:
                break
            
            # Take first value for automatic workflow
            first_value = possible_values[0]['value']
            
            # Apply filter
            filter_result = session['cli'].add_filter(
                char_num=char_num,
                value=first_value,
                output_format='json'
            )
            
            steps.append({
                'step': step + 1,
                'character': proposal['character'],
                'selected_value': {
                    'value': first_value,
                    'description': possible_values[0]['description']
                },
                'remaining_items': filter_result.get('remaining_items', 0)
            })
            
            if filter_result.get('remaining_items', 0) <= 1:
                break
        
        # Get final state
        final_state = session['cli'].show_state(output_format='json')
        
        return jsonify({
            'status': 'success',
            'steps': steps,
            'final_state': final_state
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Serve React app in production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app"""
    static_folder = os.path.join(os.path.dirname(__file__), 'build')
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    else:
        return send_from_directory(static_folder, 'index.html')

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists('delta.db'):
        print("Error: delta.db not found. Run 'python3 delta_parser.py' first.")
        sys.exit(1)
    
    print("Starting DELTA API server...")
    print("Database: delta.db")
    print("API endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/database/stats")
    print("  GET  /api/propose")
    print("  POST /api/filter")
    print("  GET  /api/state")
    print("  DELETE /api/state")
    print("  POST /api/undo")
    print("  GET  /api/character/<id>/values")
    print("  GET  /api/character/<id>/info")
    print("  GET  /api/items")
    print("  POST /api/workflow/auto")
    
    app.run(debug=True, host='0.0.0.0', port=5001)