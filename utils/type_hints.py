# Shared type hints

from typing import Tuple, Union
from numpy import ndarray

Size = Tuple[int, int]

PixelBuffer = ndarray

# Generally only RGBA is used since Blender seems to always use full RGBA for Images
RPixel = Tuple[float]
RGPixel = Tuple[float, float]
RGBPixel = Tuple[float, float, float]
RGBAPixel = Tuple[float, float, float, float]
Pixel = Union[RPixel, RGPixel, RGBPixel, RGBAPixel]

PixelBufferOrPixel = Union[PixelBuffer, Pixel]

Corner = Tuple[int, int]
Box = Tuple[int, int, int, int]
CornerOrBox = Union[Corner, Box]
