import os
import logging
import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from config.config import Config

# Import Blueprints
from api.temperature import temperature_bp
from api.vegetation import vegetation_bp
from api.heat_islands import heat_islands_bp
from api.recommendations import recommendations_bp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('FLASK_DEBUG') == 'True' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    # Note: Allows all origins for dev simplicity, use env var in prod
    
    # Register Blueprints
    app.register_blueprint(temperature_bp, url_prefix='/api')
    app.register_blueprint(vegetation_bp, url_prefix='/api')
    app.register_blueprint(heat_islands_bp, url_prefix='/api')
    app.register_blueprint(recommendations_bp, url_prefix='/api')
    
    # Routes
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check with route listing."""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(str(rule))
            
        return jsonify({
            'status': 'healthy',
            'service': 'Urban Heat Island Mapper API',
            'version': '1.0.0',
            'routes': sorted(routes)
        })
    
    @app.route('/api/info', methods=['GET'])
    def api_info():
        """Return API information and data status."""
        data_dir = Path(__file__).resolve().parent / ".." / "data" / "processed"
        
        # Check files
        files_status = {
            "temperature_raster": (data_dir / "temperature_la.tif").exists(),
            "ndvi_raster": (data_dir / "ndvi_la.tif").exists(),
            "heat_islands_json": (data_dir / "heat_islands.json").exists(),
            "vegetation_analysis_json": (data_dir / "vegetation_analysis.json").exists()
        }
        
        return jsonify({
            'name': 'Urban Heat Island Mapper API',
            'version': '1.0.0',
            'description': 'Geospatial API for analyzing urban heat islands',
            'data_status': files_status,
            'last_updated': datetime.datetime.now().isoformat()
        })
    
    @app.route('/api/test', methods=['GET'])
    def test_endpoint():
        return jsonify({
            'message': 'Backend connection successful',
            'debug_mode': app.config['DEBUG']
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Server Error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
        
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG') == 'True'
    
    logger.info(f"Starting server on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
