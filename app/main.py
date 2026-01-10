"""
Flask application factory.
"""
from flask import Flask

from app.config.settings import Config


def create_app(config_class=Config) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Configured Flask application instance
    """
    import os
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(project_root, 'static')
    
    app = Flask(__name__, static_folder=static_folder, static_url_path='/static')
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints
    from app.interface.http.blueprints.health_bp import health_bp
    from app.interface.http.blueprints.nba_bp import nba_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(nba_bp)
    
    # Serve index.html at root
    @app.route('/')
    def index():
        """Serve the main index.html file."""
        from flask import send_from_directory
        return send_from_directory(static_folder, 'index.html')
    
    # Initialize database tables on startup
    try:
        from app.infrastructure.database.migrations import create_tables
        create_tables(config_class)
    except Exception as e:
        # Log but don't fail startup if DB is not ready yet
        import logging
        logging.warning(f"Could not initialize database tables: {e}")
    
    # Register error handlers
    from app.interface.http.errors.handlers import register_error_handlers
    register_error_handlers(app)
    
    return app

