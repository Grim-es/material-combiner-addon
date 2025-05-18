"""RectPack2D - 2D rectangle bin packing algorithm.

This module provides a Python implementation of the RectPack2D algorithm
originally written in C++ by TeamHypersomnia. The algorithm efficiently
packs rectangles into a bin while trying to minimize the overall size.

The implementation uses a splitting heuristic to divide empty spaces after
rectangle insertion, with multiple ordering strategies to find optimal packing.

Original C++ implementation by TeamHypersomnia:
https://github.com/TeamHypersomnia/rectpack2D

Copyright (c) 2022 Patryk Czachurski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Typical usage example:
    images = {
        'mat1': {'gfx': {'size': (100, 200)}},
        'mat2': {'gfx': {'size': (150, 100)}}
    }
    packer = RectPack2D()
    packed_result = packer.pack(images)
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Union


class CallbackResult(Enum):
    """Result of callbacks for rectangle insertion.

    Used to control flow during the packing process.
    """

    ABORT_PACKING = 0
    CONTINUE_PACKING = 1


class BinDimension(Enum):
    """Dimensions for binary search on bin sizes.

    Determines which dimensions to consider when searching for the optimal bin size.
    """

    BOTH = 0  # Search for optimal width and height
    WIDTH = 1  # Only optimize width
    HEIGHT = 2  # Only optimize height


class FlippingOption(Enum):
    """Options for flipping rectangles.

    Controls whether rectangles can be rotated during packing.
    """

    DISABLED = 0  # Rectangles cannot be flipped
    ENABLED = 1  # Rectangles can be flipped (rotated 90 degrees)


class RectWH:
    """Rectangle with width and height.

    A simple rectangle representation with width and height properties.
    Used as a base for other rectangle types in the algorithm.

    Attributes:
        w: Width of the rectangle.
        h: Height of the rectangle.
    """

    def __init__(self, w: int = 0, h: int = 0) -> None:
        """Initialize a rectangle with width and height.

        Args:
            w: Width of the rectangle. Defaults to 0.
            h: Height of the rectangle. Defaults to 0.
        """
        self.w = w
        self.h = h

    def flip(self) -> "RectWH":
        """Swap width and height.

        Returns:
            Self after flipping for method chaining.
        """
        self.w, self.h = self.h, self.w
        return self

    def max_side(self) -> int:
        """Get the maximum side length.

        Returns:
            Length of the longer side.
        """
        return max(self.w, self.h)

    def min_side(self) -> int:
        """Get the minimum side length.

        Returns:
            Length of the shorter side.
        """
        return min(self.w, self.h)

    def area(self) -> int:
        """Get the area of the rectangle.

        Returns:
            Area calculated as width * height.
        """
        return self.w * self.h

    def perimeter(self) -> int:
        """Get the perimeter of the rectangle.

        Returns:
            Perimeter calculated as 2 * (width + height).
        """
        return 2 * (self.w + self.h)

    def expand_with(self, r: "RectXYWH") -> None:
        """Expand this rectangle to include another rectangle.

        Updates the current rectangle's dimensions to ensure it
        encompasses the given rectangle.

        Args:
            r: Another rectangle with position and size.
        """
        self.w = max(self.w, r.x + r.w)
        self.h = max(self.h, r.y + r.h)


class RectXYWH:
    """Rectangle with position (x, y) and size (width, height).

    Extends the basic rectangle by adding position coordinates.

    Attributes:
        x: X-coordinate of the top-left corner.
        y: Y-coordinate of the top-left corner.
        w: Width of the rectangle.
        h: Height of the rectangle.
    """

    def __init__(self, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> None:
        """Initialize a rectangle with position and size.

        Args:
            x: X-coordinate of the top-left corner. Defaults to 0.
            y: Y-coordinate of the top-left corner. Defaults to 0.
            w: Width of the rectangle. Defaults to 0.
            h: Height of the rectangle. Defaults to 0.
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def area(self) -> int:
        """Get the area of the rectangle.

        Returns:
            Area calculated as width * height.
        """
        return self.w * self.h

    def perimeter(self) -> int:
        """Get the perimeter of the rectangle.

        Returns:
            Perimeter calculated as 2 * (width + height).
        """
        return 2 * (self.w + self.h)

    def get_wh(self) -> RectWH:
        """Get width and height as RectWH.

        Returns:
            A RectWH object with the same dimensions.
        """
        return RectWH(self.w, self.h)


class RectXYWHF(RectXYWH):
    """Rectangle with position, size, and flipped flag.

    Extends RectXYWH by adding a flag to indicate if the rectangle
    has been rotated (width and height swapped).

    Attributes:
        x: X-coordinate of the top-left corner.
        y: Y-coordinate of the top-left corner.
        w: Width of the rectangle (after possible flipping).
        h: Height of the rectangle (after possible flipping).
        flipped: Whether the rectangle has been flipped.
    """

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        w: int = 0,
        h: int = 0,
        flipped: bool = False,
    ) -> None:
        """Initialize a rectangle with position, size, and flipped state.

        Args:
            x: X-coordinate of the top-left corner. Defaults to 0.
            y: Y-coordinate of the top-left corner. Defaults to 0.
            w: Original width of the rectangle. Defaults to 0.
            h: Original height of the rectangle. Defaults to 0.
            flipped: Whether the rectangle is flipped. If True, width and height
                are swapped. Defaults to False.
        """
        super().__init__(x, y, w if not flipped else h, h if not flipped else w)
        self.flipped = flipped

    def get_wh(self) -> RectWH:
        """Get width and height as RectWH.

        Returns:
            A RectWH object with the current dimensions.
        """
        return RectWH(self.w, self.h)


# Type alias for spaces
SpaceRect = RectXYWH

# Constants
MAX_SPLITS = 2  # Maximum number of splits for a space
DEFAULT_DISCARD_STEP = 1  # Step size for bin size optimization


class CreatedSplits:
    """Splits created after inserting a rectangle.

    Manages the spaces created after placing a rectangle in a larger space.
    These splits represent the remaining empty areas.

    Attributes:
        count: Number of splits created.
        spaces: List of space rectangles.
    """

    def __init__(self, *spaces) -> None:
        """Initialize with provided spaces.

        Args:
            *spaces: Variable number of SpaceRect objects.
        """
        self.count = len(spaces)
        self.spaces = list(spaces)
        if len(spaces) < MAX_SPLITS:
            self.spaces.append(None)
            if len(spaces) < 1:
                self.spaces.append(None)

    @staticmethod
    def failed() -> "CreatedSplits":
        """Create a failed splits instance.

        Used when a rectangle cannot be inserted into a space.

        Returns:
            A CreatedSplits instance marked as failed.
        """
        result = CreatedSplits()
        result.count = -1
        return result

    @staticmethod
    def none() -> "CreatedSplits":
        """Create an empty splits instance.

        Used when a rectangle fits exactly into a space with no remainder.

        Returns:
            An empty CreatedSplits instance.
        """
        return CreatedSplits()

    def better_than(self, other: "CreatedSplits") -> bool:
        """Check if this split is better than another.

        Fewer splits are considered better as it reduces fragmentation.

        Args:
            other: Another CreatedSplits instance to compare with.

        Returns:
            True if this split is better than the other, False otherwise.
        """
        return self.count < other.count

    def __bool__(self) -> bool:
        """Convert to boolean.

        Returns:
            True if this is not a failed split, False otherwise.
        """
        return self.count != -1


def insert_and_split(im: RectWH, sp: SpaceRect) -> CreatedSplits:
    """Insert a rectangle into a space and create splits if needed.

    This function is the core of the packing algorithm. It attempts to place
    a rectangle in a given space and creates optimal splits for the remaining area.

    Args:
        im: Image rectangle to insert.
        sp: Space rectangle to insert into.

    Returns:
        CreatedSplits instance containing the resulting splits after insertion.
        Returns failed splits if the rectangle doesn't fit.
    """
    free_w = sp.w - im.w
    free_h = sp.h - im.h

    if free_w < 0 or free_h < 0:
        # Image is bigger than the candidate empty space
        return CreatedSplits.failed()

    if free_w == 0 and free_h == 0:
        # Image fits exactly
        return CreatedSplits.none()

    # Image fits with one dimension exactly
    if free_w > 0 and free_h == 0:
        r = SpaceRect(sp.x + im.w, sp.y, free_w, sp.h)
        return CreatedSplits(r)

    if free_w == 0 and free_h > 0:
        r = SpaceRect(sp.x, sp.y + im.h, sp.w, free_h)
        return CreatedSplits(r)

    # Image is strictly smaller than the space
    # Decide how to split based on which free dimension is larger
    if free_w > free_h:
        # Split horizontally first (wider free space)
        bigger_split = SpaceRect(sp.x + im.w, sp.y, free_w, sp.h)
        lesser_split = SpaceRect(sp.x, sp.y + im.h, im.w, free_h)
        return CreatedSplits(bigger_split, lesser_split)

    # Split vertically first (taller free space)
    bigger_split = SpaceRect(sp.x, sp.y + im.h, sp.w, free_h)
    lesser_split = SpaceRect(sp.x + im.w, sp.y, free_w, im.h)
    return CreatedSplits(bigger_split, lesser_split)


class DefaultEmptySpaces:
    """Default implementation of empty spaces storage.

    Manages a collection of empty spaces in the bin.

    Attributes:
        empty_spaces: List of empty space rectangles.
    """

    def __init__(self) -> None:
        """Initialize an empty collection of spaces."""
        self.empty_spaces = []

    def remove(self, i: int) -> None:
        """Remove a space at the given index.

        Efficiently removes by swapping with the last element.

        Args:
            i: Index of the space to remove.
        """
        self.empty_spaces[i] = self.empty_spaces[-1]
        self.empty_spaces.pop()

    def add(self, r: SpaceRect) -> bool:
        """Add a space to the collection.

        Args:
            r: Space rectangle to add.

        Returns:
            True indicating successful addition.
        """
        self.empty_spaces.append(r)
        return True

    def get_count(self) -> int:
        """Get a number of spaces in the collection.

        Returns:
            Number of empty spaces.
        """
        return len(self.empty_spaces)

    def reset(self) -> None:
        """Reset the collection by removing all spaces."""
        self.empty_spaces.clear()

    def get(self, i: int) -> SpaceRect:
        """Get space at the given index.

        Args:
            i: Index of the space to retrieve.

        Returns:
            The space rectangle at the specified index.
        """
        return self.empty_spaces[i]


class EmptySpaces:
    """Manager for empty spaces in a bin.

    Handles the insertion of rectangles and management of remaining empty spaces.

    Attributes:
        current_aabb: Axis-aligned bounding box of all inserted rectangles.
        spaces: Storage for empty spaces.
        flipping_mode: Whether rectangles can be flipped during insertion.
        allow_flip: Whether flipping is allowed in general.
    """

    def __init__(self, r: RectWH) -> None:
        """Initialize with a rectangle representing the initial bin size.

        Args:
            r: Rectangle representing the initial bin dimensions.
        """
        self.current_aabb = RectWH()
        self.spaces = DefaultEmptySpaces()
        self.flipping_mode = FlippingOption.ENABLED
        self.allow_flip = True
        self.reset(r)

    def reset(self, r: RectWH) -> None:
        """Reset with a new rectangle.

        Clears all existing spaces and creates a single space with the given dimensions.

        Args:
            r: Rectangle representing the new bin dimensions.
        """
        self.current_aabb = RectWH()
        self.spaces.reset()
        self.spaces.add(SpaceRect(0, 0, r.w, r.h))

    @staticmethod
    def _try_insertion(
        image_rectangle: RectWH,
        candidate_space: SpaceRect,
        try_flipping: bool,
    ) -> Tuple[bool, bool, Optional[CreatedSplits]]:
        """Try to insert a rectangle, optionally with flipping.

        Helper method to reduce complexity in the main insert method.

        Args:
            image_rectangle: Rectangle to insert
            candidate_space: Space to insert into
            try_flipping: Whether to try flipping the rectangle

        Returns:
            Tuple of (insertion_successful, should_flip, splits_to_use)
        """
        # Try normal orientation
        normal = insert_and_split(image_rectangle, candidate_space)

        # Try flipped orientation if allowed
        flipped = None
        if try_flipping:
            flipped_wh = RectWH(image_rectangle.w, image_rectangle.h).flip()
            flipped = insert_and_split(flipped_wh, candidate_space)

        # Determine best insertion strategy
        if normal and flipped:
            if flipped.better_than(normal):
                return True, True, flipped
            return True, False, normal
        elif normal:
            return True, False, normal
        elif flipped:
            return True, True, flipped

        return False, False, None

    def _create_result_rect(
        self,
        candidate_space: SpaceRect,
        image_rectangle: RectWH,
        should_flip: bool,
    ) -> Union[RectXYWH, RectXYWHF]:
        """Create the resulting rectangle after successful insertion.

        Args:
            candidate_space: Space where the rectangle was inserted
            image_rectangle: Original rectangle dimensions
            should_flip: Whether the rectangle should be flipped

        Returns:
            Rectangle with position information
        """
        if self.allow_flip:
            return RectXYWHF(
                candidate_space.x,
                candidate_space.y,
                image_rectangle.w,
                image_rectangle.h,
                should_flip,
            )
        else:
            return RectXYWH(
                candidate_space.x,
                candidate_space.y,
                image_rectangle.w,
                image_rectangle.h,
            )

    def insert(
        self,
        image_rectangle: RectWH,
    ) -> Optional[Union[RectXYWH, RectXYWHF]]:
        """Insert a rectangle into the bin.

        Attempts to find the best place to insert the rectangle within the available
        empty spaces. Can optionally flip the rectangle if that produces a better fit.

        Args:
            image_rectangle: Rectangle to insert.

        Returns:
            Inserted rectangle with position information, or None if insertion failed.
        """
        try_flipping = (
            self.allow_flip and self.flipping_mode == FlippingOption.ENABLED
        )

        for i in range(self.spaces.get_count() - 1, -1, -1):
            candidate_space = self.spaces.get(i)

            # Try insertion with optional flipping
            should_insert, should_flip, splits_to_use = self._try_insertion(
                image_rectangle, candidate_space, try_flipping
            )

            # If insertion is possible
            if should_insert:
                # Remove the space we're using
                self.spaces.remove(i)

                # Add the new splits
                for s in range(splits_to_use.count):
                    if not self.spaces.add(splits_to_use.spaces[s]):
                        return None

                # Create and return the result rectangle
                result = self._create_result_rect(
                    candidate_space, image_rectangle, should_flip
                )

                # Update the bounding box
                self.current_aabb.expand_with(result)
                return result

        # No suitable space found
        return None

    def get_rects_aabb(self) -> RectWH:
        """Get the axis-aligned bounding box of all inserted rectangles.

        Returns:
            Bounding box as a RectWH instance.
        """
        return self.current_aabb

    def get_spaces(self) -> DefaultEmptySpaces:
        """Get the collection of empty spaces.

        Returns:
            The DefaultEmptySpaces instance managing empty spaces.
        """
        return self.spaces


class RectPack2D:
    """RectPack2D implementation for Material Combiner addon.

    This class implements the RectPack2D algorithm with an interface compatible
    with the existing BinPacker class in the addon. It packs rectangles efficiently
    using multiple strategies to find the best arrangement.

    Attributes:
        bin: Dictionary of materials and their image/size data.
    """

    @staticmethod
    def _try_pack_all_rectangles(
        rectangles: List[RectXYWHF], bin_size: RectWH
    ) -> Tuple[bool, List[RectXYWHF]]:
        """Try to pack all rectangles into a bin of the given size.

        Args:
            rectangles: List of rectangles to pack
            bin_size: Size of the bin to pack into

        Returns:
            Tuple of (success, packed_rectangles)
        """
        # Create a copy of rectangles to avoid modifying originals
        rects_copy = [RectXYWHF(0, 0, r.w, r.h) for r in rectangles]
        for i, r in enumerate(rects_copy):
            r.material_id = rectangles[i].material_id

        # Create an empty spaces manager for this bin size
        packing_root = EmptySpaces(bin_size)

        # Try to insert all rectangles
        all_inserted = True
        for rect in rects_copy:
            inserted_rect = packing_root.insert(rect.get_wh())
            if inserted_rect is None:
                all_inserted = False
                break

            # Store insertion results
            rect.x = inserted_rect.x
            rect.y = inserted_rect.y
            rect.flipped = getattr(inserted_rect, "flipped", False)

        return all_inserted, rects_copy

    def _find_best_bin_size(  # noqa: PLR0915
        self,
        rectangles: List[RectXYWHF],
        max_bin_side: int,
        discard_step: int = DEFAULT_DISCARD_STEP,
    ) -> Tuple[RectWH, List[RectXYWHF]]:
        """Find the best bin size through binary search.

        Implements the binary search algorithm from the original rectpack2D.

        Args:
            rectangles: List of rectangles to pack
            max_bin_side: Maximum size for the bin
            discard_step: Step size for optimization (default: 1 for the highest precision)

        Returns:
            Tuple of (best_bin_size, packed_rectangles)
        """
        # Strategy 1: Optimize both width and height
        best_bin = RectWH(max_bin_side, max_bin_side)

        def try_with_dimension(  # noqa: PLR0912, PLR0915
            dim: BinDimension, current_best: RectWH
        ) -> Tuple[RectWH, Optional[List[RectXYWHF]]]:
            """Try to find the best bin size by optimizing specific dimensions.

            Args:
                dim: Which dimension(s) to optimize
                current_best: Current best bin size to start from

            Returns:
                Tuple of (best_bin, best_packing)
            """
            candidate_bin = RectWH(current_best.w, current_best.h)

            # Initial step size depends on the dimension
            if dim == BinDimension.BOTH:
                candidate_bin.w //= 2
                candidate_bin.h //= 2
                step = candidate_bin.w // 2
            elif dim == BinDimension.WIDTH:
                candidate_bin.w //= 2
                step = candidate_bin.w // 2
            else:  # HEIGHT
                candidate_bin.h //= 2
                step = candidate_bin.h // 2

            best_result = None

            while True:
                success, packed_rects = self._try_pack_all_rectangles(
                    rectangles, candidate_bin
                )

                if success:
                    # Successfully packed - try with a smaller bin
                    prev_success_bin = RectWH(candidate_bin.w, candidate_bin.h)
                    best_result = packed_rects

                    # Check if we've reached the optimization threshold
                    if step <= abs(discard_step):
                        # If discard_step is negative, make additional precise attempts
                        if discard_step < 0 and abs(discard_step) > 1:
                            remaining_precise = abs(discard_step)
                            precise_step = 1

                            while (
                                remaining_precise > 0 and step <= precise_step
                            ):
                                if dim == BinDimension.BOTH:
                                    candidate_bin.w -= precise_step
                                    candidate_bin.h -= precise_step
                                elif dim == BinDimension.WIDTH:
                                    candidate_bin.w -= precise_step
                                else:
                                    candidate_bin.h -= precise_step

                                success, new_packed = (
                                    self._try_pack_all_rectangles(
                                        rectangles, candidate_bin
                                    )
                                )

                                if success:
                                    prev_success_bin = RectWH(
                                        candidate_bin.w, candidate_bin.h
                                    )
                                    best_result = new_packed
                                    remaining_precise -= 1
                                else:
                                    # Restore the last successful size
                                    if dim == BinDimension.BOTH:
                                        candidate_bin.w += precise_step
                                        candidate_bin.h += precise_step
                                    elif dim == BinDimension.WIDTH:
                                        candidate_bin.w += precise_step
                                    else:
                                        candidate_bin.h += precise_step
                                    break

                        return prev_success_bin, best_result

                    # Reduce the candidate bin size
                    if dim == BinDimension.BOTH:
                        candidate_bin.w -= step
                        candidate_bin.h -= step
                    elif dim == BinDimension.WIDTH:
                        candidate_bin.w -= step
                    else:
                        candidate_bin.h -= step

                elif dim == BinDimension.BOTH:
                    # Failed to pack - try with a bigger bin
                    candidate_bin.w += step
                    candidate_bin.h += step
                    # Check if we've exceeded the starting bin size
                    if candidate_bin.area() > current_best.area():
                        return current_best, best_result
                elif dim == BinDimension.WIDTH:
                    candidate_bin.w += step
                    if candidate_bin.w > current_best.w:
                        return current_best, best_result
                else:
                    candidate_bin.h += step
                    if candidate_bin.h > current_best.h:
                        return current_best, best_result

                # Update step size for the next iteration
                step = max(1, step // 2)

        # Try optimizing both dimensions first
        best_bin, best_packing = try_with_dimension(BinDimension.BOTH, best_bin)

        if best_packing:
            # Try optimizing width only
            width_bin, width_packing = try_with_dimension(
                BinDimension.WIDTH, best_bin
            )
            if width_packing and width_bin.area() < best_bin.area():
                best_bin = width_bin
                best_packing = width_packing

            # Try optimizing height only
            height_bin, height_packing = try_with_dimension(
                BinDimension.HEIGHT, best_bin
            )
            if height_packing and height_bin.area() < best_bin.area():
                best_bin = height_bin
                best_packing = height_packing

        return best_bin, best_packing or []

    def pack(self, images: Dict) -> Dict:
        """Packs the given images into a single bin.

        This method places all textures in optimal positions within the atlas.
        It updates each texture's entry with position data in the 'fit' field.

        The algorithm tries multiple sorting strategies to find the optimal packing:
        1. By area (decreasing)
        2. By perimeter (decreasing)
        3. By maximum side length (decreasing)
        4. By width (decreasing)
        5. By height (decreasing)

        For each strategy, it uses binary search to find the smallest possible bin
        size that can fit all rectangles, optimizing for square-like outputs.

        Args:
            images: Dictionary of materials and their image/size data.
                    Each item should have the format:
                    {material_id: {'gfx': {'size': (width, height)}}}

        Returns:
            The updated bin dictionary with position information in each item's
            'gfx.fit' field, containing x, y coordinates, width and height.
        """
        self.bin = images

        # Prepare all rectangles for packing
        rectangles = []
        for material_id, image_data in self.bin.items():
            w, h = image_data["gfx"]["size"]
            rect = RectXYWHF(0, 0, w, h)
            # Store reference to original material_id
            rect.material_id = material_id
            rectangles.append(rect)

        # Calculate a reasonable maximum bin size
        total_area = sum(r.area() for r in rectangles)
        max_dimension = max(max(r.w, r.h) for r in rectangles)
        max_bin_side = min(
            max(max_dimension * 2, int(total_area**0.5 * 1.5)),
            20000,  # Max texture size limit
        )

        # Try to pack with different ordering strategies
        best_area = float("inf")
        best_packing = None

        # Define different ordering strategies
        strategies = [
            lambda a, b: a.area() > b.area(),  # By area (decreasing)
            lambda a, b: a.perimeter()
            > b.perimeter(),  # By perimeter (decreasing)
            lambda a, b: max(a.w, a.h)
            > max(b.w, b.h),  # By max side (decreasing)
            lambda a, b: a.w > b.w,  # By width (decreasing)
            lambda a, b: a.h > b.h,  # By height (decreasing)
        ]

        for strategy in strategies:
            # Use the original sorting approach that worked
            sorted_rects = sorted(
                rectangles, key=lambda r: (strategy(r, r), id(r))
            )

            # Find the best bin size for this ordering
            bin_size, packed_rects = self._find_best_bin_size(
                sorted_rects, max_bin_side, discard_step=-4
            )

            if packed_rects:
                area = bin_size.area()

                # Improved square-ness calculation:
                # More quadratic penalty for fewer square bins, but still keeping
                # area as the primary factor
                aspect_ratio = max(
                    bin_size.w / bin_size.h, bin_size.h / bin_size.w
                )
                # Quadratic growth of penalty
                square_penalty = (aspect_ratio - 1) ** 2
                # Slightly stronger penalty
                area_with_penalty = area * (1 + square_penalty * 0.15)

                if area_with_penalty < best_area:
                    best_area = area_with_penalty
                    best_packing = {r.material_id: {
                        'x': r.x,
                        'y': r.y,
                        'flipped': r.flipped
                    } for r in packed_rects}

        # If we found packing, update the bin
        if best_packing:
            for material_id, pack_data in best_packing.items():
                original_size = self.bin[material_id]["gfx"]["size"]
                # Update the 'fit' field in the original format expected by the addon
                self.bin[material_id]["gfx"]["fit"] = {
                    'x': pack_data['x'],
                    'y': pack_data['y'],
                    'w': original_size[1] if pack_data['flipped'] else original_size[0],
                    'h': original_size[0] if pack_data['flipped'] else original_size[1]
                }

        return self.bin
