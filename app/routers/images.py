from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services import histogram_service as hsvc
from app.services.store import image_store
from app.schemas import UploadResponse

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Charge une image ('image réelle') et la convertit en image
    numérique (cf. section 1.2.1 du cours) : en niveaux de gris, ou en
    couleur (3 plans R, V, B) si le fichier source est en couleur."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    try:
        gray, color = hsvc.load_image(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Image illisible: {exc}") from exc

    record = image_store.save(filename=file.filename or "image", gray=gray, color=color)
    stats = hsvc.compute_stats(gray).as_dict()
    h, w = gray.shape
    return UploadResponse(
        image_id=record.image_id, filename=record.filename,
        width=w, height=h, is_color=record.is_color, stats=stats,
    )


@router.get("/{image_id}/png")
async def get_image_png(image_id: str):
    record = image_store.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Image introuvable.")
    png_bytes = hsvc.array_to_png_bytes(record.color if record.color is not None else record.gray)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/{image_id}/stats")
async def get_image_stats(image_id: str):
    record = image_store.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Image introuvable.")
    return hsvc.compute_stats(record.gray).as_dict()
