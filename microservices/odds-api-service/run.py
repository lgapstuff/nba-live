"""
Entry point for running the Odds API microservice.
"""
from app.main import create_app

app = create_app()

if __name__ == "__main__":
    import os
    from app.config.settings import Config
    
    port = int(os.getenv("APP_PORT", Config.APP_PORT))
    host = os.getenv("APP_HOST", Config.APP_HOST)
    app.run(host=host, port=port, debug=Config.FLASK_DEBUG)
