from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    image_id: str
    filename: str
    width: int
    height: int
    is_color: bool = False
    stats: dict


class HistogramData(BaseModel):
    image_id: str
    levels: list[int]
    counts: list[int]
    cdf: list[float]
    stats: dict


class ProcessResponse(BaseModel):
    """Réponse standard pour les opérations qui produisent une nouvelle
    image dérivée (égalisation, spécification, seuillage, morphologie...)."""
    source_image_id: str
    result_image_id: str
    operation: str
    is_color: bool = False
    params: dict = Field(default_factory=dict)
    stats_before: dict
    stats_after: dict


class SpecifyProfileRequest(BaseModel):
    image_id: str
    profile: str = Field(..., description="uniform | gaussian | exponential | bimodal")
    mean: Optional[float] = 128.0
    std: Optional[float] = 40.0
    rate: Optional[float] = 0.02
    invert: Optional[bool] = False
    m1: Optional[float] = 60
    s1: Optional[float] = 20
    m2: Optional[float] = 190
    s2: Optional[float] = 20
    w1: Optional[float] = 0.5


class SpecifyReferenceRequest(BaseModel):
    image_id: str
    reference_image_id: str


class ThresholdRequest(BaseModel):
    image_id: str
    mode: str = Field("otsu", description="manual | otsu")
    low: Optional[int] = 0
    high: Optional[int] = 255


class MorphologyRequest(BaseModel):
    image_id: str
    operation: str = Field(..., description="erode | dilate | opening | closing | gradient | tophat | skeleton")
    shape: str = Field("disk", description="disk | square | cross")
    size: int = 1
    h: Optional[int] = 0


class ParticleAnalysisRequest(BaseModel):
    image_id: str
    connectivity: int = 8
    min_area: int = 4
    n_classes: int = 8
