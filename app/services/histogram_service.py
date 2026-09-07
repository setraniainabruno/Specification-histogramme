from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image

N_LEVELS = 256  # image numérique codée sur 8 bits (0..255), cf. section 2.2.1 du cours



# Chargement / export


def load_grayscale(image_bytes: bytes) -> np.ndarray:
    """Charge une image (tous formats usuels) et la convertit en niveaux de
    gris 8 bits, conformément au principe de "formation de l'image
    numérique" (section 1.2.1 / 2.2.1 du cours)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    return np.array(img, dtype=np.uint8)


def load_image(image_bytes: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Charge une image et détecte si elle est en couleur ou en niveaux de
    gris (extension du principe de "formation de l'image numérique",
    section 1.2.1 / 2.2.1 du cours, au cas d'une image couleur codée sur
    3 plans R, V, B).

    Renvoie toujours un tableau de luminance 2D ``gray`` (utilisé pour les
    statistiques, l'histogramme affiché et les opérations qui n'ont de
    sens qu'en niveaux de gris : seuillage, morphologie, mesures), et, si
    l'image source est en couleur, un tableau RGB 3D ``color`` (sinon
    ``None``).
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("L", "1", "I", "I;16"):
        gray = np.array(img.convert("L"), dtype=np.uint8)
        return gray, None

    rgb_img = img.convert("RGB")  # aplati sur fond blanc si canal alpha
    color = np.array(rgb_img, dtype=np.uint8)
    gray = np.array(rgb_img.convert("L"), dtype=np.uint8)
    return gray, color


def rgb_to_luminance(rgb: np.ndarray) -> np.ndarray:
    """Luminance perçue (pondération standard ITU-R BT.601), utilisée pour
    recalculer le canal de niveaux de gris après un traitement couleur
    canal par canal."""
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    return np.clip(lum, 0, 255).astype(np.uint8)


def array_to_png_bytes(arr: np.ndarray) -> bytes:
    """Exporte un tableau numpy en PNG : niveaux de gris (2D) ou couleur
    RGB (3D, HxWx3)."""
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB" if arr.ndim == 3 else "L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()



# Histogramme et statistiques (section 5.5 "Paramètres d'intensité" du cours)


def compute_histogram(gray: np.ndarray) -> np.ndarray:
    """Histogramme brut (nombre de pixels par niveau de gris 0..255)."""
    hist, _ = np.histogram(gray.flatten(), bins=N_LEVELS, range=(0, N_LEVELS))
    return hist.astype(np.int64)


def compute_cdf(hist: np.ndarray) -> np.ndarray:
    """Fonction de répartition cumulée normalisée (0..1)."""
    cdf = np.cumsum(hist).astype(np.float64)
    total = cdf[-1]
    if total == 0:
        return cdf
    return cdf / total


@dataclass
class IntensityStats:
    """Paramètres d'intensité / de texture simplifiés, inspirés de la
    section 5.5 (Paramètres d'intensité) et 5.6 (Paramètres de texture)
    du support de cours : moyenne, écart-type, "densité totale intégrée"
    (somme), coefficient de dissymétrie (skewness) et d'aplatissement
    (kurtosis)."""

    mean: float
    std: float
    minimum: int
    maximum: int
    median: float
    integrated_density: float  # "densité totale intégrée" (section 5.5)
    skewness: float            # coefficient de dissymétrie (section 5.6)
    kurtosis: float            # coefficient d'aplatissement (section 5.6)
    entropy: float             # richesse d'information de l'image (section 1.2.1)

    def as_dict(self) -> dict:
        return {
            "mean": round(self.mean, 3),
            "std": round(self.std, 3),
            "min": int(self.minimum),
            "max": int(self.maximum),
            "median": round(self.median, 3),
            "integrated_density": round(self.integrated_density, 1),
            "skewness": round(self.skewness, 4),
            "kurtosis": round(self.kurtosis, 4),
            "entropy": round(self.entropy, 4),
        }


def compute_stats(gray: np.ndarray) -> IntensityStats:
    flat = gray.flatten().astype(np.float64)
    mean = float(np.mean(flat))
    std = float(np.std(flat))
    hist = compute_histogram(gray)
    probs = hist / hist.sum() if hist.sum() > 0 else hist.astype(np.float64)
    nz = probs[probs > 0]
    entropy = float(-(nz * np.log2(nz)).sum())

    if std > 1e-9:
        skew = float(np.mean(((flat - mean) / std) ** 3))
        kurt = float(np.mean(((flat - mean) / std) ** 4) - 3.0)
    else:
        skew, kurt = 0.0, 0.0

    return IntensityStats(
        mean=mean,
        std=std,
        minimum=int(flat.min()),
        maximum=int(flat.max()),
        median=float(np.median(flat)),
        integrated_density=float(flat.sum()),
        skewness=skew,
        kurtosis=kurt,
        entropy=entropy,
    )


# Distributions théoriques cibles (utilisées quand il n'y a pas d'image de
# référence : l'utilisateur choisit un "profil" de répartition souhaité)


def target_histogram_uniform() -> np.ndarray:
    """Distribution uniforme -> équivaut à l'égalisation classique."""
    return np.ones(N_LEVELS, dtype=np.float64)


def target_histogram_gaussian(mean: float = 128.0, std: float = 40.0) -> np.ndarray:
    x = np.arange(N_LEVELS)
    hist = np.exp(-0.5 * ((x - mean) / max(std, 1e-6)) ** 2)
    return hist


def target_histogram_exponential(rate: float = 0.02, invert: bool = False) -> np.ndarray:
    x = np.arange(N_LEVELS)
    if invert:
        x = (N_LEVELS - 1) - x
    hist = np.exp(-rate * x)
    return hist


def target_histogram_bimodal(m1: float = 60, s1: float = 20, m2: float = 190, s2: float = 20,
                              w1: float = 0.5) -> np.ndarray:
    x = np.arange(N_LEVELS)
    g1 = np.exp(-0.5 * ((x - m1) / max(s1, 1e-6)) ** 2)
    g2 = np.exp(-0.5 * ((x - m2) / max(s2, 1e-6)) ** 2)
    return w1 * g1 + (1 - w1) * g2


TARGET_PROFILES = {
    "uniform": target_histogram_uniform,
    "gaussian": target_histogram_gaussian,
    "exponential": target_histogram_exponential,
    "bimodal": target_histogram_bimodal,
}



# Spécification d'histogramme (histogram matching)


def build_matching_lut(cdf_src: np.ndarray, cdf_ref: np.ndarray) -> np.ndarray:
    """Construit la table de correspondance (LUT) niveau-à-niveau qui, pour
    chaque niveau source i, choisit le niveau j de la référence dont la
    CDF est la plus proche : c'est le coeur de l'algorithme de
    spécification d'histogramme (méthode des fonctions de répartition)."""
    lut = np.zeros(N_LEVELS, dtype=np.uint8)
    ref_idx = 0
    for src_idx in range(N_LEVELS):
        # avance ref_idx tant que la CDF de référence est strictement
        # inférieure à celle de la source (les deux CDF sont croissantes)
        while ref_idx < N_LEVELS - 1 and cdf_ref[ref_idx] < cdf_src[src_idx]:
            ref_idx += 1
        lut[src_idx] = ref_idx
    return lut


def apply_lut(gray: np.ndarray, lut: np.ndarray) -> np.ndarray:
    return lut[gray]


def equalize_histogram(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Égalisation classique = cas particulier de la spécification, avec
    une distribution cible uniforme."""
    hist_src = compute_histogram(gray)
    cdf_src = compute_cdf(hist_src)
    cdf_ref = compute_cdf(target_histogram_uniform())
    lut = build_matching_lut(cdf_src, cdf_ref)
    return apply_lut(gray, lut), lut


def specify_histogram_from_reference(gray: np.ndarray, reference_gray: np.ndarray
                                      ) -> tuple[np.ndarray, np.ndarray]:
    """Spécification d'histogramme à partir d'une image de référence
    fournie par l'utilisateur."""
    hist_src = compute_histogram(gray)
    hist_ref = compute_histogram(reference_gray)
    cdf_src = compute_cdf(hist_src)
    cdf_ref = compute_cdf(hist_ref)
    lut = build_matching_lut(cdf_src, cdf_ref)
    return apply_lut(gray, lut), lut


def specify_histogram_from_profile(gray: np.ndarray, profile: str, **kwargs
                                    ) -> tuple[np.ndarray, np.ndarray]:
    """Spécification d'histogramme à partir d'un profil théorique
    (gaussien, exponentiel, bimodal, uniforme)."""
    if profile not in TARGET_PROFILES:
        raise ValueError(f"Profil inconnu: {profile}")
    hist_src = compute_histogram(gray)
    hist_ref = TARGET_PROFILES[profile](**kwargs)
    cdf_src = compute_cdf(hist_src)
    cdf_ref = compute_cdf(hist_ref)
    lut = build_matching_lut(cdf_src, cdf_ref)
    return apply_lut(gray, lut), lut



# Seuillage (section 3.1 du cours) — fourni en complément car le cours en
# fait "une étape clé du traitement de l'image" : transformation de
# l'image numérique en image binaire.


def threshold_manual(gray: np.ndarray, low: int, high: Optional[int] = None) -> np.ndarray:
    """Seuillage simple ou double seuil, tel que décrit section 3.1 :
    pixels dont le niveau de gris est compris entre low et high -> 1
    (255 pour la visualisation), les autres -> 0."""
    if high is None:
        high = N_LEVELS - 1
    mask = (gray >= low) & (gray <= high)
    return (mask.astype(np.uint8)) * 255


def threshold_otsu(gray: np.ndarray) -> tuple[np.ndarray, int]:
    """Seuillage automatique par la méthode d'Otsu (maximisation de la
    variance inter-classes) — un choix de seuil automatique complémentaire
    au seuillage manuel décrit dans le cours."""
    hist = compute_histogram(gray).astype(np.float64)
    total = hist.sum()
    if total == 0:
        return np.zeros_like(gray), 0

    sum_total = np.dot(np.arange(N_LEVELS), hist)
    sum_bg, weight_bg = 0.0, 0.0
    max_var, best_t = 0.0, 0

    for t in range(N_LEVELS):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        between_var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if between_var > max_var:
            max_var = between_var
            best_t = t

    binary = threshold_manual(gray, best_t, N_LEVELS - 1)
    return binary, best_t



# Extension aux images couleur : les opérations d'histogramme (égalisation,
# spécification) sont appliquées indépendamment à chacun des trois plans
# R, V, B (chaque plan étant lui-même une "image numérique" au sens de la
# section 2.2.1 du cours), puis les plans traités sont recombinés. Le
# seuillage et la morphologie mathématique, eux, n'ont de sens que sur une
# image en niveaux de gris (ou binaire) : ils continuent de s'appliquer sur
# la luminance de l'image couleur (voir routers/histogram.py et
# routers/morphology.py).


def equalize_color(rgb: np.ndarray) -> np.ndarray:
    """Égalisation d'histogramme appliquée indépendamment à chaque canal
    R, V, B d'une image couleur."""
    out = np.empty_like(rgb)
    for c in range(3):
        out[:, :, c], _ = equalize_histogram(rgb[:, :, c])
    return out


def specify_profile_color(rgb: np.ndarray, profile: str, **kwargs) -> np.ndarray:
    """Spécification d'histogramme (profil théorique), canal par canal,
    pour une image couleur."""
    out = np.empty_like(rgb)
    for c in range(3):
        out[:, :, c], _ = specify_histogram_from_profile(rgb[:, :, c], profile, **kwargs)
    return out


def specify_reference_color(rgb: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Spécification d'histogramme à partir d'une image de référence, pour
    une image couleur. Si la référence est elle-même couleur, chaque canal
    est mis en correspondance avec le canal de même nom (R->R, V->V, B->B).
    Si la référence est en niveaux de gris, les trois canaux de la source
    sont tous mis en correspondance avec cette même distribution de
    luminance (l'image résultat garde alors la teinte de la source mais en
    adopte le contraste global)."""
    out = np.empty_like(rgb)
    if reference.ndim == 3:
        for c in range(3):
            out[:, :, c], _ = specify_histogram_from_reference(rgb[:, :, c], reference[:, :, c])
    else:
        for c in range(3):
            out[:, :, c], _ = specify_histogram_from_reference(rgb[:, :, c], reference)
    return out
