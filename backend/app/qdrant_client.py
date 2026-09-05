import logging
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.config import settings

logger = logging.getLogger("medical_rag.qdrant")

_qdrant_client_instance: Optional[QdrantClient] = None


def close_qdrant_client() -> None:
    """Close the shared Qdrant client before Python interpreter teardown.

    This matters for embedded Qdrant: leaving cleanup to ``QdrantClient.__del__``
    can make it run after Python has removed import hooks, producing an otherwise
    harmless ``sys.meta_path is None`` shutdown warning.
    """
    global _qdrant_client_instance
    client = _qdrant_client_instance
    _qdrant_client_instance = None
    if client is not None:
        client.close()

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client_instance
    if _qdrant_client_instance is None:
        if settings.QDRANT_URL.strip().lower() in {"local", "embedded"}:
            storage_path = settings.QDRANT_PATH
            if not os.path.isabs(storage_path):
                storage_path = os.path.join(os.getcwd(), storage_path)
            logger.info("Using embedded Qdrant storage at %s", storage_path)
            _qdrant_client_instance = QdrantClient(path=storage_path)
        else:
            kwargs = {}
            if settings.QDRANT_API_KEY:
                kwargs["api_key"] = settings.QDRANT_API_KEY
            _qdrant_client_instance = QdrantClient(url=settings.QDRANT_URL, **kwargs)
    return _qdrant_client_instance

def init_qdrant_collection() -> bool:
    """Initialize Qdrant collection and create payload index for patient_id."""
    client = get_qdrant_client()
    try:
        collections = client.get_collections().collections
        exists = any(c.name == settings.QDRANT_COLLECTION for c in collections)
        
        if not exists:
            logger.info(f"Creating Qdrant collection: {settings.QDRANT_COLLECTION}")
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            # Create payload index on patient_id for strict filtering
            client.create_payload_index(
                collection_name=settings.QDRANT_COLLECTION,
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logger.info("Collection and payload index created successfully.")
        else:
            logger.info(f"Collection {settings.QDRANT_COLLECTION} already exists.")
        return True
    except Exception as e:
        logger.error(f"Error initializing Qdrant collection: {e}")
        return False

def store_chunks_in_qdrant(points: List[PointStruct]) -> bool:
    """Upsert vector points into Qdrant."""
    client = get_qdrant_client()
    try:
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points
        )
        return True
    except Exception as e:
        logger.error(f"Error upserting points to Qdrant: {e}")
        raise e

def search_patient_chunks(patient_id: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """Strictly search chunks belonging ONLY to the target patient_id."""
    client = get_qdrant_client()
    try:
        patient_filter = Filter(
            must=[
                FieldCondition(
                    key="patient_id",
                    match=MatchValue(value=patient_id)
                )
            ]
        )
        
        # qdrant-client 1.18+ replaced ``search`` with ``query_points``.
        # Access the returned points explicitly before building source data.
        search_results = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            query_filter=patient_filter,
            limit=limit,
            with_payload=True
        ).points
        
        results = []
        for res in search_results:
            results.append({
                "id": str(res.id),
                "score": float(res.score),
                "text": res.payload.get("text", ""),
                "filename": res.payload.get("filename", "Unknown Document"),
                "page": res.payload.get("page", 1),
                "chunk_index": res.payload.get("chunk_index", 0),
                "patient_id": res.payload.get("patient_id", patient_id),
                "document_type": res.payload.get("document_type", "document")
            })
        return results
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}")
        raise e

def get_all_patients_from_qdrant() -> List[str]:
    """Retrieve distinct patient IDs stored in Qdrant payload."""
    client = get_qdrant_client()
    try:
        if not client.collection_exists(settings.QDRANT_COLLECTION):
            return []
        
        scroll_res, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=500,
            with_payload=True,
            with_vectors=False
        )
        
        patient_ids = set()
        for point in scroll_res:
            pid = point.payload.get("patient_id")
            if pid:
                patient_ids.add(pid)
        return sorted(list(patient_ids))
    except Exception as e:
        logger.error(f"Error fetching patient list: {e}")
        return []

def delete_patient_from_qdrant(patient_id: str) -> bool:
    """Delete all chunks and vectors belonging to a specific patient_id."""
    client = get_qdrant_client()
    try:
        clean_pid = patient_id.strip().upper()
        patient_filter = Filter(
            must=[
                FieldCondition(
                    key="patient_id",
                    match=MatchValue(value=clean_pid)
                )
            ]
        )
        scroll_res, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=patient_filter,
            limit=5000,
            with_payload=False,
            with_vectors=False
        )
        point_ids = [p.id for p in scroll_res]
        if point_ids:
            client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=models.PointIdsList(points=point_ids)
            )
        logger.info(f"Deleted {len(point_ids)} records for patient: {clean_pid}")
        return True
    except Exception as e:
        logger.error(f"Error deleting patient {patient_id}: {e}")
        return False

def clear_all_patients_from_qdrant() -> bool:
    """Purge all points from the Qdrant collection to remove all patient records."""
    client = get_qdrant_client()
    try:
        scroll_res, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=5000,
            with_payload=False,
            with_vectors=False
        )
        point_ids = [p.id for p in scroll_res]
        if point_ids:
            client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=models.PointIdsList(points=point_ids)
            )
        logger.info(f"Purged {len(point_ids)} records from {settings.QDRANT_COLLECTION}")
        return True
    except Exception as e:
        logger.error(f"Error clearing Qdrant collection: {e}")
        return False

def get_patient_documents_summary(patient_id: str) -> Dict[str, Any]:
    """Retrieve unique document filenames and chunk counts stored in Qdrant for a patient."""
    client = get_qdrant_client()
    try:
        clean_pid = patient_id.strip()
        scroll_res, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=5000,
            with_payload=True,
            with_vectors=False
        )
        
        files_map = {}
        total_patient_chunks = 0
        for point in scroll_res:
            p_payload = point.payload or {}
            pid = str(p_payload.get("patient_id", "")).strip()
            if pid.upper() == clean_pid.upper():
                total_patient_chunks += 1
                fname = p_payload.get("filename", "Unknown Document")
                doc_type = p_payload.get("document_type", "Document")
                if fname not in files_map:
                    files_map[fname] = {"filename": fname, "document_type": doc_type, "chunks": 0}
                files_map[fname]["chunks"] += 1
            
        file_list = list(files_map.values())
        return {
            "patient_id": clean_pid.upper(),
            "has_documents": len(file_list) > 0,
            "total_documents": len(file_list),
            "total_chunks": total_patient_chunks,
            "documents": file_list
        }
    except Exception as e:
        logger.error(f"Error fetching patient documents: {e}")
        return {
            "patient_id": patient_id,
            "has_documents": False,
            "total_documents": 0,
            "total_chunks": 0,
            "documents": []
        }

