from flask import Flask
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["JSON_SORT_KEYS"] = False

    from .routes import main
    app.register_blueprint(main)
    return app
