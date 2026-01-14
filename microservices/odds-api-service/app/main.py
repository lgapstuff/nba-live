"""
Flask application factory for Odds API microservice.
"""
from flask import Flask
from flask_cors import CORS

from app.config.settings import Config
from app.infrastructure.clients.odds_api_client import OddsAPIClient
from app.interface.http.controllers.odds_controller import create_odds_controller


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize Odds API client
    if not config_class.THE_ODDS_API_KEY:
        raise ValueError("THE_ODDS_API_KEY environment variable is required")
    
    odds_client = OddsAPIClient(
        api_key=config_class.THE_ODDS_API_KEY,
        base_url=config_class.THE_ODDS_API_BASE_URL
    )
    
    # Register blueprints
    odds_bp = create_odds_controller(odds_client)
    app.register_blueprint(odds_bp)
    
    # Health check at root
    @app.route("/")
    def root():
        return {
            "service": "odds-api-service",
            "status": "running",
            "version": "1.0.0"
        }
    
    return app
