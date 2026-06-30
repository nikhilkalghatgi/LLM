"""Documents router: list the data pipeline's ingested-document metadata."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_current_principal
from auth.security import Principal
from db.database import session_scope
from db.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: str
    filename: str
    tenant_id: str
    status: str
    chunk_count: int
    error: str
    created_at: Optional[str] = None
    ingested_at: Optional[str] = None


def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        tenant_id=doc.tenant_id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error=doc.error or "",
        created_at=doc.created_at.isoformat() if doc.created_at else None,
        ingested_at=doc.ingested_at.isoformat() if doc.ingested_at else None,
    )


@router.get("", response_model=List[DocumentOut])
def list_documents(
    principal: Principal = Depends(get_current_principal),
) -> List[DocumentOut]:
    """List documents ingested under the caller's tenant (newest first)."""
    with session_scope() as session:
        rows = (
            session.query(Document)
            .filter(Document.tenant_id == principal.tenant_id)
            .order_by(Document.created_at.desc())
            .all()
        )
        return [_to_out(d) for d in rows]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str, principal: Principal = Depends(get_current_principal)
) -> DocumentOut:
    """Fetch one document's metadata (tenant-scoped)."""
    with session_scope() as session:
        doc = session.get(Document, document_id)
        if doc is None or doc.tenant_id != principal.tenant_id:
            raise HTTPException(status_code=404, detail="Document not found.")
        return _to_out(doc)
