from flask import Blueprint, send_file, jsonify
from bson import ObjectId
from io import BytesIO
from .. import db as coredb

files_bp = Blueprint("files", __name__, url_prefix="/files")

@files_bp.get("/<file_id>")
def get_file(file_id):
    try:
        f = coredb.fs().get(ObjectId(file_id))
    except Exception:
        return jsonify(erro="Arquivo não encontrado"), 404
    return send_file(BytesIO(f.read()),
                     mimetype=getattr(f, "content_type", "application/octet-stream"),
                     as_attachment=False,
                     download_name=getattr(f, "filename", "file"))
