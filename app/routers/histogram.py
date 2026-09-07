from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import histogram_service as hsvc
from app.services.store import image_store
from app.schemas import (
    HistogramData, ProcessResponse, SpecifyProfileRequest,
    SpecifyReferenceRequest, ThresholdRequest,
)

router = APIRouter(prefix="/api/histogram", tags=["histogram"])


def _get_or_404(image_id: str):
    record = image_store.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' introuvable.")
    return record


@router.get("/{image_id}", response_model=HistogramData)
async def get_histogram(image_id: str):
    record = _get_or_404(image_id)
    hist = hsvc.compute_histogram(record.gray)
    cdf = hsvc.compute_cdf(hist)
    stats = hsvc.compute_stats(record.gray).as_dict()
    return HistogramData(
        image_id=image_id,
        levels=list(range(hsvc.N_LEVELS)),
        counts=hist.tolist(),
        cdf=[round(float(v), 5) for v in cdf],
        stats=stats,
    )


@router.get("/profile/{profile}")
async def get_target_profile(profile: str, mean: float = 128, std: float = 40,
                              rate: float = 0.02, invert: bool = False,
                              m1: float = 60, s1: float = 20, m2: float = 190,
                              s2: float = 20, w1: float = 0.5):
    """Renvoie la forme d'histogramme théorique (pour prévisualisation
    avant de lancer la spécification)."""
    if profile not in hsvc.TARGET_PROFILES:
        raise HTTPException(status_code=400, detail="Profil inconnu.")
    kwargs = {}
    if profile == "gaussian":
        kwargs = {"mean": mean, "std": std}
    elif profile == "exponential":
        kwargs = {"rate": rate, "invert": invert}
    elif profile == "bimodal":
        kwargs = {"m1": m1, "s1": s1, "m2": m2, "s2": s2, "w1": w1}
    hist = hsvc.TARGET_PROFILES[profile](**kwargs)
    hist = hist / hist.sum() * (256 * 256)  # mise à l'échelle indicative
    return {"levels": list(range(hsvc.N_LEVELS)), "counts": [round(float(v), 2) for v in hist]}


@router.post("/equalize", response_model=ProcessResponse)
async def equalize(image_id: str):
    record = _get_or_404(image_id)
    stats_before = hsvc.compute_stats(record.gray).as_dict()

    if record.is_color:
        color_result = hsvc.equalize_color(record.color)
        gray_result = hsvc.rgb_to_luminance(color_result)
    else:
        gray_result, _lut = hsvc.equalize_histogram(record.gray)
        color_result = None

    new_record = image_store.save(filename=f"eq_{record.filename}", gray=gray_result, color=color_result)
    stats_after = hsvc.compute_stats(gray_result).as_dict()
    return ProcessResponse(
        source_image_id=image_id, result_image_id=new_record.image_id,
        operation="equalize", is_color=new_record.is_color,
        params={"channels": "R,V,B (indépendants)"} if record.is_color else {},
        stats_before=stats_before, stats_after=stats_after,
    )


@router.post("/specify/reference", response_model=ProcessResponse)
async def specify_from_reference(req: SpecifyReferenceRequest):
    record = _get_or_404(req.image_id)
    reference = _get_or_404(req.reference_image_id)
    stats_before = hsvc.compute_stats(record.gray).as_dict()

    if record.is_color:
        ref_array = reference.color if reference.is_color else reference.gray
        color_result = hsvc.specify_reference_color(record.color, ref_array)
        gray_result = hsvc.rgb_to_luminance(color_result)
    else:
        gray_result, _lut = hsvc.specify_histogram_from_reference(record.gray, reference.gray)
        color_result = None

    new_record = image_store.save(filename=f"spec_{record.filename}", gray=gray_result, color=color_result)
    stats_after = hsvc.compute_stats(gray_result).as_dict()
    params = {"reference_image_id": req.reference_image_id}
    if record.is_color:
        params["channels"] = "R,V,B (indépendants)" if reference.is_color else "R,V,B → luminance de la référence"
    return ProcessResponse(
        source_image_id=req.image_id, result_image_id=new_record.image_id,
        operation="specify_reference", is_color=new_record.is_color,
        params=params,
        stats_before=stats_before, stats_after=stats_after,
    )


@router.post("/specify/profile", response_model=ProcessResponse)
async def specify_from_profile(req: SpecifyProfileRequest):
    record = _get_or_404(req.image_id)
    stats_before = hsvc.compute_stats(record.gray).as_dict()

    kwargs = {}
    if req.profile == "gaussian":
        kwargs = {"mean": req.mean, "std": req.std}
    elif req.profile == "exponential":
        kwargs = {"rate": req.rate, "invert": req.invert}
    elif req.profile == "bimodal":
        kwargs = {"m1": req.m1, "s1": req.s1, "m2": req.m2, "s2": req.s2, "w1": req.w1}

    try:
        if record.is_color:
            color_result = hsvc.specify_profile_color(record.color, req.profile, **kwargs)
            gray_result = hsvc.rgb_to_luminance(color_result)
        else:
            gray_result, _lut = hsvc.specify_histogram_from_profile(record.gray, req.profile, **kwargs)
            color_result = None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_record = image_store.save(filename=f"spec_{record.filename}", gray=gray_result, color=color_result)
    stats_after = hsvc.compute_stats(gray_result).as_dict()
    params = {"profile": req.profile, **kwargs}
    if record.is_color:
        params["channels"] = "R,V,B (indépendants)"
    return ProcessResponse(
        source_image_id=req.image_id, result_image_id=new_record.image_id,
        operation="specify_profile", is_color=new_record.is_color,
        params=params,
        stats_before=stats_before, stats_after=stats_after,
    )


@router.post("/threshold", response_model=ProcessResponse)
async def threshold(req: ThresholdRequest):
    """Seuillage manuel ou automatique (Otsu) — section 3.1 du cours.
    S'applique toujours sur la luminance de l'image (le résultat est une
    image binaire, en niveaux de gris, même si la source est en couleur)."""
    record = _get_or_404(req.image_id)
    stats_before = hsvc.compute_stats(record.gray).as_dict()

    if req.mode == "otsu":
        result, t = hsvc.threshold_otsu(record.gray)
        params = {"mode": "otsu", "computed_threshold": t}
    elif req.mode == "manual":
        result = hsvc.threshold_manual(record.gray, req.low or 0, req.high or 255)
        params = {"mode": "manual", "low": req.low, "high": req.high}
    else:
        raise HTTPException(status_code=400, detail="mode doit être 'manual' ou 'otsu'.")

    if record.is_color:
        params["note"] = "Seuillage effectué sur la luminance de l'image source (résultat en niveaux de gris)."

    new_record = image_store.save(filename=f"thresh_{record.filename}", gray=result)
    stats_after = hsvc.compute_stats(result).as_dict()
    return ProcessResponse(
        source_image_id=req.image_id, result_image_id=new_record.image_id,
        operation="threshold", is_color=False, params=params,
        stats_before=stats_before, stats_after=stats_after,
    )
