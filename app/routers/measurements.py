from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.routers.morphology import _to_binary01
from app.services import measurement_service as msvc
from app.services.store import image_store
from app.schemas import ParticleAnalysisRequest

router = APIRouter(prefix="/api/measurements", tags=["measurements"])


def _get_or_404(image_id: str):
    record = image_store.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' introuvable.")
    return record


@router.post("/particles")
async def analyze_particles(req: ParticleAnalysisRequest):
    """Dénombrement (5.2), granulométrie en nombre (5.3.2) et paramètres
    de forme (5.4) sur une image binaire (seuillée au préalable si besoin
    via Otsu)."""
    record = _get_or_404(req.image_id)
    binary01 = _to_binary01(record.gray)

    particles = msvc.analyze_particles(
        binary01, connectivity=req.connectivity, min_area=req.min_area,
    )
    summary = msvc.granulometry_summary(binary01, particles, n_classes=req.n_classes)

    return {
        "image_id": req.image_id,
        "summary": summary.as_dict(),
        "particles": [p.as_dict() for p in particles[:500]],  # borne l'affichage
        "truncated": len(particles) > 500,
    }
