from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from bson import ObjectId
from .. import db as coredb
from io import BytesIO

pdfs_bp = Blueprint("pdfs", __name__, url_prefix="/pdfs")

@pdfs_bp.post("")
def upload_pdf():
    """
    Form data:
      - reference_key (str) -> chave que identifica este PDF-base (ex: 'alfabeto_v1')
      - file (PDF)
    """
    reference_key = (request.form.get("reference_key") or "").strip()
    f = request.files.get("file")

    if not reference_key:
        return jsonify(erro="reference_key é obrigatório"), 400
    if not f or f.mimetype != "application/pdf":
        return jsonify(erro="Envie um PDF válido em 'file'"), 400

    data = f.read()
    file_id = coredb.put_gridfs_if_new(
        data=data,
        filename=secure_filename(f.filename or "reference.pdf"),
        content_type=f.mimetype,
        kind="reference_pdf"
    )
    coredb.upsert_reference_pdf(
        reference_key=reference_key,
        file_id=file_id,
        filename=f.filename,
        content_type=f.mimetype
    )
    return jsonify(message="PDF cadastrado/atualizado", file_id=str(file_id), reference_key=reference_key)

@pdfs_bp.get("")
def list_pdfs():
    cur = coredb.db()["reference_pdfs"].find().sort("created_at", -1)
    out = []
    for d in cur:
        out.append({
            "reference_key": d.get("reference_key"),
            "file_id": str(d.get("file_id")),
            "filename": d.get("filename"),
            "content_type": d.get("content_type"),
            "created_at": d.get("created_at")
        })
    return jsonify(out)

@pdfs_bp.get("/<reference_key>/download")
def download_pdf(reference_key):
    ref = coredb.get_reference_by_key(reference_key)
    if not ref:
        return jsonify(erro="PDF não encontrado"), 404

    file_id = ref.get("file_id")
    file_obj = coredb.fs().get(ObjectId(file_id))
    if not file_obj:
        return jsonify(erro="Arquivo não encontrado no GridFS"), 404

    return send_file(
        BytesIO(file_obj.read()),
        mimetype=file_obj.content_type or "application/pdf",
        as_attachment=False,
        download_name=file_obj.filename or "arquivo.pdf"
    )