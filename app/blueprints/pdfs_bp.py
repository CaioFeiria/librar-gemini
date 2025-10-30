from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from bson import ObjectId
from io import BytesIO
from .. import db as coredb

pdfs_bp = Blueprint("pdfs", __name__, url_prefix="/pdfs")

@pdfs_bp.post("")
def upload_letter_pdf():
    """
    Form-data:
      - letter (Texto) -> ex.: A, B, C...
      - file (Arquivo) -> application/pdf
    Armazena/atualiza o PDF para a letra informada.
    """
    letter = (request.form.get("letter") or "").strip().upper()
    f = request.files.get("file")

    if not letter:
        return jsonify(erro="letter é obrigatório"), 400
    if not f or f.mimetype != "application/pdf":
        return jsonify(erro="Envie um PDF válido em 'file'"), 400

    data = f.read()
    file_id = coredb.put_gridfs_if_new(
        data=data,
        filename=secure_filename(f.filename or f"{letter}.pdf"),
        content_type=f.mimetype,
        kind="letter_pdf"
    )
    coredb.upsert_letter_pdf(
        letter=letter,
        file_id=file_id,
        filename=f.filename,
        content_type=f.mimetype
    )
    return jsonify(message="PDF da letra cadastrado/atualizado",
                   letter=letter,
                   file_id=str(file_id))

@pdfs_bp.get("")
def list_letter_pdfs():
    """
    Lista PDFs por letra.
    """
    cur = coredb.db()["letter_pdfs"].find().sort("letter", 1)
    out = []
    for d in cur:
        out.append({
            "letter": d.get("letter"),
            "file_id": str(d.get("file_id")),
            "filename": d.get("filename"),
            "content_type": d.get("content_type"),
            "created_at": d.get("created_at")
        })
    return jsonify(out)

@pdfs_bp.get("/<letter>/download")
def download_letter_pdf(letter: str):
    """
    Faz o download/visualização do PDF da letra.
    """
    doc = coredb.get_pdf_by_letter(letter)
    if not doc:
        return jsonify(erro="PDF da letra não encontrado"), 404

    file_id = doc.get("file_id")
    fobj = coredb.fs().get(ObjectId(file_id))
    return send_file(
        BytesIO(fobj.read()),
        mimetype=getattr(fobj, "content_type", "application/pdf"),
        as_attachment=False,
        download_name=getattr(fobj, "filename", f"{doc.get('letter','?')}.pdf")
    )
