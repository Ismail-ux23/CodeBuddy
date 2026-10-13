from flask import Flask
from routes import api

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "demo-only-not-a-real-secret"
    app.register_blueprint(api)
    return app
