from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from bson import ObjectId
from .. import db as coredb
from ..services.gemini_service import evaluate_letter
from ..services.storage_service import log_validation

validate_bp = Blueprint("validate", __name__)

@validate_bp.post("/validate-libras")
def validate_libras():
    """
    Form data:
      - letter: str (ex: 'A')
      - photo: file (image/*)
      - pdf_file_id: str (opcional) -> ID do PDF salvo no Mongo (GridFS)
    """
    letter = (request.form.get("letter") or "").strip()
    pdf_file_id = (request.form.get("pdf_file_id") or "").strip()
    photo = request.files.get("photo")

    if not letter:
        return jsonify(erro="Campo 'letter' é obrigatório"), 400
    if not photo or not (photo.mimetype or "").startswith("image/"):
        return jsonify(erro="Envie uma foto válida (image/*) no campo 'photo'"), 400

    # ========== 1) Buscar o PDF ==========
    if pdf_file_id:
        try:
            pdf_bytes = coredb.get_file_bytes(ObjectId(pdf_file_id))
            pdf_meta = {"file_id": pdf_file_id}
        except Exception:
            return jsonify(erro="PDF não encontrado no banco para o ID informado"), 404
    else:
        # Fallback: usa o mais recente se não for enviado o ID
        ref = coredb.get_latest_reference()
        if not ref:
            return jsonify(erro="Nenhum PDF encontrado. Envie o campo 'pdf_file_id' ou cadastre um em /pdfs"), 404
        pdf_file_id = str(ref["file_id"])
        pdf_bytes = coredb.get_file_bytes(ObjectId(pdf_file_id))
        pdf_meta = {"file_id": pdf_file_id}

    # ========== 2) Ler a foto ==========
    photo_bytes = photo.read()
    photo_file_id = coredb.put_gridfs_if_new(
        data=photo_bytes,
        filename=secure_filename(photo.filename or "photo"),
        content_type=photo.mimetype,
        kind="student_photo"
    )

    # ========== 3) Chamar o Gemini ==========
    from flask import current_app
    model_name = current_app.config["GEMINI_MODEL"]

    result_text, finish_reason = evaluate_letter(
        model_name=model_name,
        letter=letter,
        photo_mime=photo.mimetype,
        photo_bytes=photo_bytes,
        pdf_mime="application/pdf",
        pdf_bytes=pdf_bytes
    )

    # ========== 4) Logar no banco ==========
    log_validation(
        letter=letter,
        photo_file_id=photo_file_id,
        pdf_file_id=ObjectId(pdf_file_id),
        model=model_name,
        result_text=result_text,
        finish_reason=finish_reason,
        photo_meta={
            "filename": photo.filename,
            "content_type": photo.mimetype,
            "size_bytes": len(photo_bytes)
        },
        pdf_meta=pdf_meta
    )

    # ========== 5) Retorno ==========
    if result_text:
        return jsonify({
            "resultado": result_text,
            "finish_reason": finish_reason,
            "photo_file_id": str(photo_file_id),
            "pdf_file_id": pdf_file_id
        }), 200

    return jsonify({
        "erro": "A resposta do modelo foi bloqueada ou vazia.",
        "finish_reason": finish_reason or "DESCONHECIDO",
        "photo_file_id": str(photo_file_id),
        "pdf_file_id": pdf_file_id
    }), 502
