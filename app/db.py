from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
import gridfs
from hashlib import sha256
from datetime import datetime
from typing import Optional, Tuple

_client = None
_db = None
_fs = None

def init_mongo(uri: str, dbname: str):
    global _client, _db, _fs
    _client = MongoClient(uri)
    _db = _client[dbname]
    _fs = gridfs.GridFS(_db)

    # Índices idempotentes
    _db["fs.files"].create_index(
        [("metadata.sha256", ASCENDING)],
        name="metadata_sha256_idx",
        unique=True,
        sparse=True
    )
    # Agora armazenamos 1 PDF por letra
    _db["letter_pdfs"].create_index(
        [("letter", ASCENDING)],
        unique=True,
        name="letter_unique_idx"
    )
    _db["letter_pdfs"].create_index(
        [("created_at", DESCENDING)],
        name="letter_created_desc"
    )
    _db["validations"].create_index(
        [("created_at", DESCENDING)],
        name="val_created_desc"
    )
    return _db, _fs

def db(): return _db
def fs(): return _fs

def _sha256_bytes(b: bytes) -> str:
    h = sha256(); h.update(b); return h.hexdigest()

def put_gridfs_if_new(data: bytes, filename: str, content_type: str, kind: str) -> ObjectId:
    """
    Salva no GridFS com deduplicação por sha256 em metadata.
    """
    s = _sha256_bytes(data)
    existing = _db["fs.files"].find_one({"metadata.sha256": s}, {"_id": 1})
    if existing:
        return existing["_id"]

    return _fs.put(
        data,
        filename=filename,
        contentType=content_type,
        metadata={"sha256": s, "kind": kind},
        uploadDate=datetime.utcnow()
    )

def upsert_letter_pdf(letter: str, file_id: ObjectId, filename: str, content_type: str):
    """
    Registra/atualiza o PDF associado a uma letra.
    """
    letter = (letter or "").strip().upper()
    _db["letter_pdfs"].update_one(
        {"letter": letter},
        {"$set": {
            "letter": letter,
            "file_id": file_id,
            "filename": filename,
            "content_type": content_type,
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )

def get_pdf_by_letter(letter: str) -> Optional[dict]:
    """
    Retorna o doc da letra (com file_id) ou None.
    """
    letter = (letter or "").strip().upper()
    return _db["letter_pdfs"].find_one({"letter": letter})

def get_file_bytes(file_id: ObjectId) -> bytes:
    f = _fs.get(file_id)
    return f.read()
