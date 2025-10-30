from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from bson import ObjectId
from .. import db as coredb
from ..services.gemini_service import evaluate_letter
from ..services.storage_service import log_validation
from flask import current_app

validate_bp = Blueprint("validate", __name__)

@validate_bp.post("/validate-libras")
def validate_libras():
    """
    Form-data:
      - letter: str (ex.: 'A')  -> usado para buscar o PDF correspondente
      - photo: file (image/*)   -> foto do aluno
    """
    letter = (request.form.get("letter") or "").strip().upper()
    photo = request.files.get("photo")

    if not letter:
        return jsonify(erro="Campo 'letter' é obrigatório"), 400
    if not photo or not (photo.mimetype or "").startswith("image/"):
        return jsonify(erro="Envie uma foto válida (image/*) no campo 'photo'"), 400

    # 1) Buscar PDF da letra
    doc = coredb.get_pdf_by_letter(letter)
    if not doc:
        return jsonify(erro=f"PDF da letra '{letter}' não cadastrado"), 404

    pdf_file_id = doc["file_id"]
    pdf_bytes = coredb.get_file_bytes(ObjectId(pdf_file_id))

    # 2) Ler/salvar foto (GridFS p/ auditoria)
    photo_bytes = photo.read()
    photo_file_id = coredb.put_gridfs_if_new(
        data=photo_bytes,
        filename=secure_filename(photo.filename or "photo"),
        content_type=photo.mimetype,
        kind="student_photo"
    )

    # 3) Chamar Gemini
    model_name = current_app.config["GEMINI_MODEL"]
    result_text, finish_reason = evaluate_letter(
        model_name=model_name,
        letter=letter,
        photo_mime=photo.mimetype,
        photo_bytes=photo_bytes,
        pdf_mime="application/pdf",
        pdf_bytes=pdf_bytes
    )

    # 4) Logar
    log_validation(
        letter=letter,
        photo_file_id=photo_file_id,
        pdf_file_id=ObjectId(pdf_file_id),
        model=model_name,
        result_text=result_text,
        finish_reason=finish_reason,
        photo_meta={
            "filename": photo.filename, "content_type": photo.mimetype, "size_bytes": len(photo_bytes)
        },
        pdf_meta={
            "letter": letter, "filename": doc.get("filename"), "content_type": doc.get("content_type")
        }
    )

    # 5) Retorno
    if result_text:
        return jsonify({
            "resultado": result_text,
            "finish_reason": finish_reason,
            "letter": letter,
            "photo_file_id": str(photo_file_id),
            "pdf_file_id": str(pdf_file_id)
        }), 200

    return jsonify({
        "erro": "A resposta do modelo foi bloqueada ou vazia.",
        "finish_reason": finish_reason or "DESCONHECIDO",
        "letter": letter,
        "photo_file_id": str(photo_file_id),
        "pdf_file_id": str(pdf_file_id)
    }), 502
