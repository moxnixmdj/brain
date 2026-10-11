from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class CropReceipt:
    input_path: str
    output_path: str
    input_size: tuple[int, int]
    output_size: tuple[int, int]
    box: tuple[int, int, int, int]

def crop_image(
    input_path: str | Path,
    output_path: str | Path,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> dict[str, Any]:
    from PIL import Image

    src = Path(input_path)
    dst = Path(output_path)
    coords = (left, top, right, bottom)
    if any(type(v) is not int for v in coords):
        raise TypeError("CROP_COORDINATES_MUST_BE_INTEGERS")
    if not src.is_file():
        raise FileNotFoundError(src)
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise ValueError("INVALID_CROP_BOX")
    with Image.open(src) as im:
        width, height = im.size
        if right > width or bottom > height:
            raise ValueError("CROP_BOX_OUT_OF_BOUNDS")
        out = im.crop(coords)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst)
        receipt = CropReceipt(
            input_path=str(src),
            output_path=str(dst),
            input_size=(width, height),
            output_size=out.size,
            box=coords,
        )
    return asdict(receipt)
