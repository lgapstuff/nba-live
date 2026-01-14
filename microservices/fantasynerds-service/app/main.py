"""
Flask application factory for FantasyNerds microservice.
"""
from flask import Flask
from flask_cors import CORS

from app.config.settings import Config
from app.infrastructure.clients.fantasynerds_client import FantasyNerdsClient
from app.interface.http.controllers.fantasynerds_controller import create_fantasynerds_controller


def create_app(config_class=Config) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize FantasyNerds client
    if not config_class.FANTASYNERDS_API_KEY:
        raise ValueError("FANTASYNERDS_API_KEY environment variable is required")
    
    fantasynerds_client = FantasyNerdsClient(
        api_key=config_class.FANTASYNERDS_API_KEY,
        base_url=config_class.FANTASYNERDS_BASE_URL
    )
    
    # Register blueprints
    fantasynerds_bp = create_fantasynerds_controller(fantasynerds_client)
    app.register_blueprint(fantasynerds_bp)
    
    # Health check at root
    @app.route("/")
    def root():
        return {
            "service": "fantasynerds-service",
            "status": "running",
            "version": "1.0.0"
        }
    
    return app
