from flask import Flask
from .config import Config
from . import db as coredb
from .services.gemini_service import configure_gemini
from .blueprints.pdfs_bp import pdfs_bp
from .blueprints.validate_bp import validate_bp
from .blueprints.files_bp import files_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Mongo + GridFS
    coredb.init_mongo(app.config["MONGO_URI"], app.config["MONGO_DB"])

    # Gemini
    if not app.config["GOOGLE_API_KEY"]:
        raise RuntimeError("Defina GOOGLE_API_KEY no .env")
    configure_gemini(app.config["GOOGLE_API_KEY"])

    # Rotas
    app.register_blueprint(pdfs_bp)
    app.register_blueprint(validate_bp)
    app.register_blueprint(files_bp)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app
