from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Particle:
    label: int
    area: int                  # nombre de pixels (surface, cf. 5.3)
    perimeter: int             # approximation du périmètre (contour)
    bbox: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    equivalent_diameter: float  # diamètre du cercle de même surface (5.3.2)
    circularity: float          # indice de rondeur = P^2 / (4*pi*S), cf 5.4
    centroid: tuple[float, float]

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "area": self.area,
            "perimeter": self.perimeter,
            "bbox": self.bbox,
            "equivalent_diameter": round(self.equivalent_diameter, 2),
            "circularity": round(self.circularity, 3),
            "centroid": [round(c, 1) for c in self.centroid],
        }


def label_connected_components(binary01: np.ndarray, connectivity: int = 8) -> np.ndarray:
    """Étiquetage des composantes connexes (0 = fond). Connexité 4 ou 8."""
    h, w = binary01.shape
    labels = np.zeros((h, w), dtype=np.int32)
    current_label = 0

    if connectivity == 8:
        neighbours = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        neighbours = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for i in range(h):
        for j in range(w):
            if binary01[i, j] and labels[i, j] == 0:
                current_label += 1
                q = deque([(i, j)])
                labels[i, j] = current_label
                while q:
                    y, x = q.popleft()
                    for dy, dx in neighbours:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            if binary01[ny, nx] and labels[ny, nx] == 0:
                                labels[ny, nx] = current_label
                                q.append((ny, nx))
    return labels


def _perimeter_of_mask(mask: np.ndarray) -> int:
    """Approxime le périmètre en comptant les pixels de bord (pixels de
    l'objet ayant au moins un voisin 4-connexe hors de l'objet)."""
    padded = np.pad(mask, 1, mode="constant", constant_values=0)
    up = padded[0:-2, 1:-1]
    down = padded[2:, 1:-1]
    left = padded[1:-1, 0:-2]
    right = padded[1:-1, 2:]
    border = mask & ~(up.astype(bool) & down.astype(bool) & left.astype(bool) & right.astype(bool))
    return int(border.sum())


def analyze_particles(binary01: np.ndarray, connectivity: int = 8,
                       min_area: int = 4) -> list[Particle]:
    """Dénombrement + mesures de forme/taille pour chaque particule
    (section 5.2 à 5.4 du cours)."""
    labels = label_connected_components(binary01, connectivity)
    particles: list[Particle] = []
    n_labels = labels.max()
    for lbl in range(1, n_labels + 1):
        mask = labels == lbl
        area = int(mask.sum())
        if area < min_area:
            continue
        ys, xs = np.where(mask)
        bbox = (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))
        perimeter = _perimeter_of_mask(mask)
        equivalent_diameter = float(2.0 * np.sqrt(area / np.pi))
        circularity = float((perimeter ** 2) / (4 * np.pi * area)) if area > 0 else 0.0
        centroid = (float(ys.mean()), float(xs.mean()))
        particles.append(Particle(
            label=lbl, area=area, perimeter=perimeter, bbox=bbox,
            equivalent_diameter=equivalent_diameter, circularity=circularity,
            centroid=centroid,
        ))
    return particles


@dataclass
class GranulometrySummary:
    """Synthèse granulométrique (section 5.3.2 "Granulométrie en
    nombre") : nombre de particules, compacité et histogramme des
    diamètres équivalents regroupés en classes."""
    n_particles: int
    compacity: float  # 5.3.4 : nombre de points objet / nombre total de points
    mean_diameter: float
    diameter_classes: list[str]
    diameter_counts: list[int]

    def as_dict(self) -> dict:
        return {
            "n_particles": self.n_particles,
            "compacity": round(self.compacity, 4),
            "mean_diameter": round(self.mean_diameter, 2),
            "diameter_classes": self.diameter_classes,
            "diameter_counts": self.diameter_counts,
        }


def granulometry_summary(binary01: np.ndarray, particles: list[Particle],
                          n_classes: int = 8) -> GranulometrySummary:
    total_pixels = binary01.size
    object_pixels = int(binary01.sum())
    compacity = object_pixels / total_pixels if total_pixels > 0 else 0.0

    if not particles:
        return GranulometrySummary(0, compacity, 0.0, [], [])

    diameters = np.array([p.equivalent_diameter for p in particles])
    mean_diameter = float(diameters.mean())

    d_min, d_max = float(diameters.min()), float(diameters.max())
    if d_max <= d_min:
        d_max = d_min + 1.0
    edges = np.linspace(d_min, d_max, n_classes + 1)
    counts, _ = np.histogram(diameters, bins=edges)
    classes = [f"{edges[i]:.1f}-{edges[i+1]:.1f}" for i in range(n_classes)]

    return GranulometrySummary(
        n_particles=len(particles),
        compacity=compacity,
        mean_diameter=mean_diameter,
        diameter_classes=classes,
        diameter_counts=counts.astype(int).tolist(),
    )
