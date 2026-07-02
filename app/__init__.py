from flask import Flask
import logging

from app.config import load_configurations, configure_logging
from .views import webhook_blueprint


def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)
    logging.info("Kabisa WhatsApp RAG assistant initialized")

    return app
