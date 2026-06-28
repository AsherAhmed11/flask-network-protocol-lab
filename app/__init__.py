# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'  # route name used for @login_required redirect

def create_app(config_object='instance.config.DevelopmentConfig'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    # ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)
    login.init_app(app)

    # register blueprint (we'll keep all routes in app.routes via blueprint 'main')
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
