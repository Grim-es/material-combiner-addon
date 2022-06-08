from typing import Tuple, Union
from numpy import ndarray

Size = Tuple[int, int]

PixelBuffer = ndarray

RPixel = Tuple[float]
RGPixel = Tuple[float, float]
RGBPixel = Tuple[float, float, float]
RGBAPixel = Tuple[float, float, float, float]
Pixel = Union[RGPixel, RGPixel, RGBPixel, RGBAPixel]

PixelBufferOrPixel = Union[PixelBuffer, Pixel]

Corner = Tuple[int, int]
Box = Tuple[int, int, int, int]
CornerOrBox = Union[Corner, Box]
