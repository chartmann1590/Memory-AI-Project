# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Redirect for unauthenticated access

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Register authentication blueprint
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Register dashboard blueprint
    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    return app
