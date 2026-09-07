from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException

from app.services import histogram_service as hsvc
from app.services import morphology_service as msvc
from app.services.store import image_store
from app.schemas import MorphologyRequest, ProcessResponse

router = APIRouter(prefix="/api/morphology", tags=["morphology"])


def _get_or_404(image_id: str):
    record = image_store.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' introuvable.")
    return record


def _to_binary01(gray: np.ndarray) -> np.ndarray:
    """Convertit une image en binaire {0,1} en utilisant Otsu si elle
    n'est pas déjà binaire (0/255)."""
    unique = np.unique(gray)
    if set(unique.tolist()).issubset({0, 255}):
        return (gray > 0).astype(np.uint8)
    binary, _t = hsvc.threshold_otsu(gray)
    return (binary > 0).astype(np.uint8)


OPERATIONS = {"erode", "dilate", "opening", "closing", "gradient", "tophat", "skeleton"}


@router.post("/apply", response_model=ProcessResponse)
async def apply_morphology(req: MorphologyRequest):
    if req.operation not in OPERATIONS:
        raise HTTPException(status_code=400, detail=f"Opération inconnue: {req.operation}")

    record = _get_or_404(req.image_id)
    stats_before = hsvc.compute_stats(record.gray).as_dict()

    if req.operation == "gradient":
        result = msvc.morphological_gradient(record.gray, req.shape, req.size)
    elif req.operation == "tophat":
        result = msvc.top_hat(record.gray, req.shape, req.size, req.h or 0)
    else:
        binary01 = _to_binary01(record.gray)
        if req.operation == "erode":
            out01 = msvc.erode(binary01, req.shape, req.size)
        elif req.operation == "dilate":
            out01 = msvc.dilate(binary01, req.shape, req.size)
        elif req.operation == "opening":
            out01 = msvc.opening(binary01, req.shape, req.size)
        elif req.operation == "closing":
            out01 = msvc.closing(binary01, req.shape, req.size)
        elif req.operation == "skeleton":
            out01 = msvc.skeleton(binary01)
        else:  # pragma: no cover
            raise HTTPException(status_code=400, detail="Opération non supportée.")
        result = (out01 * 255).astype(np.uint8)

    new_record = image_store.save(filename=f"{req.operation}_{record.filename}", gray=result)
    stats_after = hsvc.compute_stats(result).as_dict()
    params = {"shape": req.shape, "size": req.size, "h": req.h}
    if record.is_color:
        params["note"] = "Opération effectuée sur la luminance de l'image source (résultat en niveaux de gris)."
    return ProcessResponse(
        source_image_id=req.image_id, result_image_id=new_record.image_id,
        operation=f"morphology_{req.operation}", is_color=False,
        params=params,
        stats_before=stats_before, stats_after=stats_after,
    )
