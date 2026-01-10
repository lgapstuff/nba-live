"""
Health check blueprint.
"""
from flask import Blueprint

from app.interface.http.controllers.health_controller import HealthController

health_bp = Blueprint("health", __name__)
controller = HealthController()


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return controller.get_health()

