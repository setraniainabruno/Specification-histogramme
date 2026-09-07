from __future__ import annotations

import numpy as np


def _structuring_element(shape: str = "disk", size: int = 3) -> np.ndarray:
    size = max(1, int(size))
    if shape == "cross":
        se = np.zeros((2 * size + 1, 2 * size + 1), dtype=bool)
        se[size, :] = True
        se[:, size] = True
        return se
    if shape == "square":
        return np.ones((2 * size + 1, 2 * size + 1), dtype=bool)
    # "disk" (disque, isotrope, cf. section 3.2.2.2 du cours)
    y, x = np.ogrid[-size:size + 1, -size:size + 1]
    return (x ** 2 + y ** 2) <= size ** 2


def _pad(binary: np.ndarray, pad: int, value: int) -> np.ndarray:
    return np.pad(binary, pad, mode="constant", constant_values=value)


def erode(binary01: np.ndarray, shape: str = "disk", size: int = 1) -> np.ndarray:
    """Erosion binaire : Y = EB(X) = {x in X / Bx inclus dans X}."""
    se = _structuring_element(shape, size)
    pad = size
    padded = _pad(binary01, pad, value=0)
    out = np.ones_like(binary01)
    offsets = np.argwhere(se) - size
    h, w = binary01.shape
    acc = np.ones((h, w), dtype=bool)
    for dy, dx in offsets:
        shifted = padded[pad + dy: pad + dy + h, pad + dx: pad + dx + w]
        acc &= shifted.astype(bool)
    out = acc.astype(np.uint8)
    return out


def dilate(binary01: np.ndarray, shape: str = "disk", size: int = 1) -> np.ndarray:
    """Dilatation binaire : Z = DB(X) = {x / X inter Bx != vide}."""
    se = _structuring_element(shape, size)
    pad = size
    padded = _pad(binary01, pad, value=0)
    offsets = np.argwhere(se) - size
    h, w = binary01.shape
    acc = np.zeros((h, w), dtype=bool)
    for dy, dx in offsets:
        shifted = padded[pad + dy: pad + dy + h, pad + dx: pad + dx + w]
        acc |= shifted.astype(bool)
    return acc.astype(np.uint8)


def opening(binary01: np.ndarray, shape: str = "disk", size: int = 1) -> np.ndarray:
    """Ouverture = érosion suivie d'une dilatation (section 3.2.2.3) :
    adoucit les contours, coupe les isthmes étroits, supprime les
    petites îles."""
    return dilate(erode(binary01, shape, size), shape, size)


def closing(binary01: np.ndarray, shape: str = "disk", size: int = 1) -> np.ndarray:
    """Fermeture = dilatation suivie d'une érosion (section 3.2.2.3) :
    bouche les canaux étroits, supprime les petits lacs."""
    return erode(dilate(binary01, shape, size), shape, size)


def morphological_gradient(gray: np.ndarray, shape: str = "disk", size: int = 1) -> np.ndarray:
    """Gradient morphologique sur image en niveaux de gris (section 3.5.2) :
    g(x) = [DB f(x) - EB f(x)] / 2. Met en évidence les zones de fort
    contraste (contours)."""
    se = _structuring_element(shape, size)
    offsets = np.argwhere(se) - size
    pad = size
    padded = gray.astype(np.int32)
    padded = np.pad(padded, pad, mode="edge")
    h, w = gray.shape
    max_img = np.full((h, w), -1, dtype=np.int32)
    min_img = np.full((h, w), 256, dtype=np.int32)
    for dy, dx in offsets:
        shifted = padded[pad + dy: pad + dy + h, pad + dx: pad + dx + w]
        max_img = np.maximum(max_img, shifted)
        min_img = np.minimum(min_img, shifted)
    grad = (max_img - min_img) // 2
    return np.clip(grad, 0, 255).astype(np.uint8)


def top_hat(gray: np.ndarray, shape: str = "disk", size: int = 3, h: int = 0) -> np.ndarray:
    """Chapeau haut de forme (section 3.5.2) : f(x) - ouverture(f)(x) - h,
    sélectionne les zones très lumineuses (petits détails clairs)."""
    se_shape, se_size = shape, size
    opened = _grayscale_opening(gray, se_shape, se_size)
    diff = gray.astype(np.int32) - opened.astype(np.int32) - h
    diff = np.clip(diff, 0, 255)
    return diff.astype(np.uint8)


def _grayscale_erode(gray: np.ndarray, shape: str, size: int) -> np.ndarray:
    se = _structuring_element(shape, size)
    offsets = np.argwhere(se) - size
    pad = size
    padded = np.pad(gray.astype(np.int32), pad, mode="edge")
    h, w = gray.shape
    out = np.full((h, w), 256, dtype=np.int32)
    for dy, dx in offsets:
        shifted = padded[pad + dy: pad + dy + h, pad + dx: pad + dx + w]
        out = np.minimum(out, shifted)
    return out.astype(np.uint8)


def _grayscale_dilate(gray: np.ndarray, shape: str, size: int) -> np.ndarray:
    se = _structuring_element(shape, size)
    offsets = np.argwhere(se) - size
    pad = size
    padded = np.pad(gray.astype(np.int32), pad, mode="edge")
    h, w = gray.shape
    out = np.full((h, w), -1, dtype=np.int32)
    for dy, dx in offsets:
        shifted = padded[pad + dy: pad + dy + h, pad + dx: pad + dx + w]
        out = np.maximum(out, shifted)
    return out.astype(np.uint8)


def _grayscale_opening(gray: np.ndarray, shape: str, size: int) -> np.ndarray:
    return _grayscale_dilate(_grayscale_erode(gray, shape, size), shape, size)


def skeleton(binary01: np.ndarray, max_iter: int = 200) -> np.ndarray:
    """Squelette simplifié obtenu par amincissements successifs
    (section 3.2.2.5 : "si on amincit un grand nombre de fois un objet...
    on tend vers un ensemble limite constitué de lignes d'épaisseur
    1 pixel"). Implémentation par l'algorithme classique de
    Zhang-Suen, qui réalise ce principe d'amincissement itératif."""
    img = binary01.astype(np.uint8).copy()
    changed = True
    it = 0
    while changed and it < max_iter:
        changed = False
        it += 1
        for step in (0, 1):
            padded = np.pad(img, 1, mode="constant", constant_values=0)
            p2 = padded[0:-2, 1:-1]
            p3 = padded[0:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, 0:-2]
            p8 = padded[1:-1, 0:-2]
            p9 = padded[0:-2, 0:-2]

            neighbours = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(neighbours)
            A = np.zeros_like(img, dtype=np.int32)
            seq = neighbours + [p2]
            for a, b in zip(seq[:-1], seq[1:]):
                A += ((a == 0) & (b == 1)).astype(np.int32)

            if step == 0:
                cond = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)

            marker = (
                (img == 1)
                & (B >= 2) & (B <= 6)
                & (A == 1)
                & cond
            )
            if marker.any():
                img[marker] = 0
                changed = True
    return img
