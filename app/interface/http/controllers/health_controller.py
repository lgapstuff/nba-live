"""
Health check controller.
"""
from flask import jsonify


class HealthController:
    """Controller for health check endpoints."""
    
    def get_health(self):
        """
        Return health status.
        
        Returns:
            JSON response with status and message
        """
        return jsonify({
            "status": "ok",
            "message": "hello from flask"
        }), 200

