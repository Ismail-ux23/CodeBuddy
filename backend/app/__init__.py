import uuid
import redis
from flask import Flask, g, jsonify, session
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError
from app.config import settings
from app.extensions import db, login, csrf, limiter, sessions


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.update(settings())
    app.config.update(overrides or {})
    app.config["SESSION_REDIS"] = redis.Redis.from_url(app.config["REDIS_URL"])
    db.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    sessions.init_app(app)
    from app.models import User

    @login.user_loader
    def load_user(ident):
        user = db.session.get(User, ident)
        return user if user and session.get("version") == user.session_version else None

    @login.unauthorized_handler
    def unauthorized():
        return error(401, "unauthorized", "Please sign in to continue.")

    @app.before_request
    def identify():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def error(status, code, message, details=None):
        if not getattr(g, "request_id", None):
            g.request_id = str(uuid.uuid4())
        return jsonify(
            error=dict(code=code, message=message, details=details, request_id=getattr(g, "request_id", ""))
        ), status

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if exc.code == 413:
            return error(
                413,
                "upload_too_large",
                f"The upload exceeds the {app.config['MAX_UPLOAD_MB']} MiB ZIP limit or multipart field limits. "
                "Upload a source-only ZIP without node_modules, .git, .venv, build outputs, or videos.",
            )
        return error(exc.code, exc.name.lower().replace(" ", "_"), exc.description)

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        return error(
            422,
            "validation",
            "Check the submitted fields.",
            [{"field": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.errorhandler(Exception)
    def unexpected(exc):
        db.session.rollback()
        if app.testing:
            raise exc
        app.logger.error("request_failed type=%s request_id=%s", type(exc).__name__, getattr(g, "request_id", ""))
        return error(500, "internal_error", "The request could not be completed. Retry or contact your administrator.")

    from app.api.routes import api
    from app.api.demo import demo

    app.register_blueprint(api, url_prefix="/api/v1")
    app.register_blueprint(demo, url_prefix="/api/v1/demo")
    return app
