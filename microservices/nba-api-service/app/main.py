"""
Flask application factory for NBA API microservice.
"""
from flask import Flask
from flask_cors import CORS

from app.config.settings import Config
from app.infrastructure.clients.nba_api_client import NBAClient
from app.interface.http.controllers.nba_controller import create_nba_controller


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize NBA API client
    nba_client = NBAClient()
    
    # Register blueprints
    nba_bp = create_nba_controller(nba_client)
    app.register_blueprint(nba_bp)
    
    # Health check at root
    @app.route("/")
    def root():
        return {
            "service": "nba-api-service",
            "status": "running",
            "version": "1.0.0"
        }
    
    return app
