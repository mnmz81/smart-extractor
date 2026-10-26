"""Make a clean page image look scanned: skew, blur, noise, grayscale. Seeded, so reproducible."""

import random
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


def degrade(img: Image.Image, seed: int, strength: float = 1.0) -> Image.Image:
    """strength scales skew, blur and noise together; 1.0 is a mild office scan."""
    rng = random.Random(seed)
    out = img.convert("L")
    out = out.rotate(
        rng.uniform(-2.0, 2.0) * strength, resample=Image.Resampling.BICUBIC, fillcolor=255
    )
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 1.2) * strength))
    noise = Image.effect_noise(out.size, min(rng.uniform(8, 20) * strength, 80))
    return ImageChops.multiply(out, noise.point(lambda v: 200 + v // 5))


def png_to_scanned_pdf(png: Path, out: Path, seed: int, strength: float = 1.0) -> None:
    with Image.open(png) as img:
        degrade(img, seed, strength).save(out, format="PDF", resolution=96.0)
