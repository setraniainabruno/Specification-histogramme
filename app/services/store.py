from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np


@dataclass
class StoredImage:
    image_id: str
    filename: str
    gray: np.ndarray
    color: np.ndarray | None = None  # None si l'image source est en niveaux de gris

    @property
    def is_color(self) -> bool:
        return self.color is not None


class ImageStore:
    def __init__(self) -> None:
        self._images: dict[str, StoredImage] = {}

    def save(self, filename: str, gray: np.ndarray, color: np.ndarray | None = None) -> StoredImage:
        image_id = uuid.uuid4().hex[:12]
        record = StoredImage(image_id=image_id, filename=filename, gray=gray, color=color)
        self._images[image_id] = record
        return record

    def get(self, image_id: str) -> StoredImage | None:
        return self._images.get(image_id)

    def replace(self, image_id: str, gray: np.ndarray, color: np.ndarray | None = None) -> StoredImage | None:
        record = self._images.get(image_id)
        if record is None:
            return None
        record.gray = gray
        record.color = color
        return record

    def all_ids(self) -> list[str]:
        return list(self._images.keys())


# instance unique partagée par l'application (singleton applicatif)
image_store = ImageStore()
