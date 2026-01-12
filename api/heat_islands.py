import logging
import json
from pathlib import Path
from flask import Blueprint, jsonify, request

# Create Blueprint
heat_islands_bp = Blueprint('heat_islands', __name__)

# Setup logging
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
HEAT_ISLANDS_PATH = DATA_DIR / "heat_islands.json"

@heat_islands_bp.route('/heat-islands/all', methods=['GET'])
def get_heat_islands():
    """
    Return all detected heat islands.
    """
    try:
        if not HEAT_ISLANDS_PATH.exists():
            return jsonify({'error': 'Heat island data not found'}), 404
            
        with open(HEAT_ISLANDS_PATH, 'r') as f:
            data = json.load(f)
            
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in get_heat_islands: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@heat_islands_bp.route('/heat-islands/summary', methods=['GET'])
def get_heat_islands_summary():
    """
    Return heat island summary statistics.
    """
    try:
        if not HEAT_ISLANDS_PATH.exists():
            return jsonify({'error': 'Heat island data not found'}), 404
            
        with open(HEAT_ISLANDS_PATH, 'r') as f:
            data = json.load(f)
            
        # If 'heat_islands' key exists (new format), use it, otherwise assume list (old format)
        islands_list = data.get('heat_islands', []) if isinstance(data, dict) else data
        
        # NOTE: If the data processing pipeline script outputs a dict with summary, we can just return that.
        # But if we need to calculate derived stats or the structure differs, we do it here.
        # The provided process_pipeline.py output structure is:
        # {
        #   'total_count': ...,
        #   'mean_temperature': ...,
        #   'threshold_used': ...,
        #   'severity_distribution': ...,
        #   'heat_islands': [...]
        # }
        # The user requester asks for:
        # {
        #    "total_islands": 8,
        #    "severity_distribution": {...},
        #    "average_intensity": 4.2,
        #    "mean_temperature": 26.8
        # }
        
        # Let's map existing data to requested format
        if isinstance(data, dict) and 'heat_islands' in data:
            # New format
            summary = {
                "total_islands": data.get('total_count', 0),
                "severity_distribution": data.get('severity_distribution', {}),
                "mean_temperature": data.get('mean_temperature', 0),
                # Average intensity needs to be calculated from islands if not in summary
                "average_intensity": 0
            }
            
            islands = data['heat_islands']
            if islands:
                avg_int = sum(i['intensity'] for i in islands) / len(islands)
                summary['average_intensity'] = round(avg_int, 2)
                
            return jsonify(summary)
            
        else:
            # Fallback for old list format if applicable
            return jsonify({'error': 'Unexpected data format'}), 500

    except Exception as e:
        logger.error(f"Error in get_heat_islands_summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@heat_islands_bp.route('/heat-islands/by-severity', methods=['GET'])
def get_heat_islands_by_severity():
    """
    Filter heat islands by severity level.
    Query param: severity (extreme/high/medium/low)
    """
    try:
        severity = request.args.get('severity')
        if not severity:
            return jsonify({'error': 'Missing severity parameter'}), 400
            
        if not HEAT_ISLANDS_PATH.exists():
            return jsonify({'error': 'Heat island data not found'}), 404
            
        with open(HEAT_ISLANDS_PATH, 'r') as f:
            data = json.load(f)
            
        islands = data.get('heat_islands', []) if isinstance(data, dict) else data
        
        filtered = [i for i in islands if i.get('severity') == severity]
        
        return jsonify(filtered)
        
    except Exception as e:
        logger.error(f"Error in get_heat_islands_by_severity: {e}")
        return jsonify({'error': 'Internal server error'}), 500
