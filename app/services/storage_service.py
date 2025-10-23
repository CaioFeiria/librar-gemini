from bson import ObjectId
from datetime import datetime
from .. import db as coredb

def log_validation(letter: str, photo_file_id: ObjectId, pdf_file_id: ObjectId,
                   model: str, result_text: str | None, finish_reason: str | None,
                   photo_meta: dict, pdf_meta: dict):
    coredb.db()["validations"].insert_one({
        "letter": letter,
        "photo_file_id": photo_file_id,
        "pdf_file_id": pdf_file_id,
        "model": model,
        "result_text": result_text,
        "finish_reason": finish_reason,
        "created_at": datetime.utcnow(),
        "photo_meta": photo_meta,
        "pdf_meta": pdf_meta
    })
