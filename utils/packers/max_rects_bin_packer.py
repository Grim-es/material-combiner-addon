"""
MIT License

Copyright (c) 2017 Yi

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

Typical usage:
    images = {
        'mat1': {'gfx': {'size': (100, 200)}},
        'mat2': {'gfx': {'size': (150, 100)}}
    }
    packer = MaxRectsBinPacker(margin=0, padding=0)
    packed_result = packer.pack(images)
"""

import math
import time
from typing import Any, Dict, List, Optional

CALCULATION_FAILED = "failed"

# Heuristic constants
HEURISTIC_BEST_SHORT_SIDE_FIT = "BSSF"
HEURISTIC_BEST_LONG_SIDE_FIT = "BLSF"
HEURISTIC_BEST_AREA_FIT = "BAF"
HEURISTIC_BOTTOM_LEFT_RULE = "BL"
HEURISTIC_CONTACT_POINT_RULE = "CP"

# Heuristic rotation rings
HEURISTIC_RING_SINGLE_BIN = {
    HEURISTIC_BEST_SHORT_SIDE_FIT: HEURISTIC_BEST_LONG_SIDE_FIT,
    HEURISTIC_BEST_LONG_SIDE_FIT: HEURISTIC_BEST_AREA_FIT,
    HEURISTIC_BEST_AREA_FIT: HEURISTIC_BOTTOM_LEFT_RULE,
    HEURISTIC_BOTTOM_LEFT_RULE: HEURISTIC_CONTACT_POINT_RULE,
}

MAX_BIN_WIDTH = 8192
MAX_BIN_HEIGHT = 8192
MAX_PADDING = 64
MAX_MARGIN = 64


class PackingError(Exception):
    """Indicates an error occurred during the packing process."""

    pass


class Rectangle:
    """Represents a rectangle with position and dimensions.

    Attributes:
        id: An identifier for the rectangle.
        left: The x-coordinate of the left edge.
        top: The y-coordinate of the top edge.
        width: The width of the rectangle.
        height: The height of the rectangle.
        right: The x-coordinate of the right edge.
        bottom: The y-coordinate of the bottom edge.
        area: The area of the rectangle.
    """

    def __init__(
        self, left: int, top: int, width: int, height: int, rect_id: str
    ):
        """Initializes a Rectangle instance.

        Args:
            left: The x-coordinate of the left edge.
            top: The y-coordinate of the top edge.
            width: The width of the rectangle.
            height: The height of the rectangle.
            rect_id: An identifier for the rectangle.
        """
        self.id = rect_id
        self.left = 0
        self.top = 0
        self.width = 0
        self.height = 0
        self.right = 0
        self.bottom = 0
        self.area = 0
        self.reset(left, top, width, height)

    def reset(self, left: int, top: int, width: int, height: int) -> None:
        """Resets the rectangle's position and dimensions.

        Args:
            left: The new x-coordinate of the left edge.
            top: The new y-coordinate of the top edge.
            width: The new width of the rectangle.
            height: The new height of the rectangle.
        """
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        self.area = self.width * self.height

    def contains(self, other_rect: "Rectangle") -> bool:
        """Checks if this rectangle completely contains another rectangle.

        Args:
            other_rect: The rectangle to check for containment.

        Returns:
            True if other_rect is contained within this rectangle, False otherwise.
        """
        return (
            other_rect.left >= self.left
            and other_rect.right <= self.right
            and other_rect.top >= self.top
            and other_rect.bottom <= self.bottom
        )

    def shrink(self, amount: int) -> None:
        """Shrinks the rectangle by a given amount on all sides.

        This is typically used to remove padding.

        Args:
            amount: The amount to shrink from each side.
        """
        self.left += amount
        self.top += amount
        self.right -= amount
        self.bottom -= amount

        padding_reduction = amount * 2
        self.width -= padding_reduction
        self.height -= padding_reduction
        # Ensure width/height don't go below zero before calculating area,
        # as the area might become negative if the shrink amount is too large for small rects.
        self.width = max(0, self.width)
        self.height = max(0, self.height)
        self.area = self.width * self.height

    def __str__(self) -> str:
        """Returns a string representation of the rectangle."""
        return "[Rect(id:{}, left:{}, top:{}, w:{}, h:{})]".format(
            self.id, self.left, self.top, self.width, self.height
        )

    def __repr__(self) -> str:
        """Returns a detailed string representation of the rectangle."""
        return self.__str__()


# --- Helper functions (static methods or module-level) ---
def _calc_surface_area(rects: List[Dict[str, Any]]) -> int:
    """Calculates the total surface area of a list of rectangle data.

    Args:
        rects: A list of dictionaries, where each dictionary represents a
            rectangle and contains 'width' and 'height' keys.

    Returns:
        The total surface area.
    """
    total_area = 0
    for rect_data in rects:
        total_area += rect_data["width"] * rect_data["height"]
    return total_area


def _calc_occupied_area(
    placed_rects: List[Rectangle], bin_width: int, bin_height: int
) -> int:
    """Calculates the area of the bounding box enclosing placed rectangles.

    Args:
        placed_rects: A list of `Rectangle` objects that have been placed.
        bin_width: The width of the bin.
        bin_height: The height of the bin.

    Returns:
        The bounding box area of the placed rectangles. Returns 0 if
        no rectangles are placed or if they have zero areas.
    """
    if not placed_rects:
        return 0

    min_left = bin_width
    max_right = 0
    min_top = bin_height
    max_bottom = 0

    for rect in placed_rects:
        min_left = min(min_left, rect.left)
        max_right = max(max_right, rect.right)
        min_top = min(min_top, rect.top)
        max_bottom = max(max_bottom, rect.bottom)

    # If no rects were processed, or they have zero areas.
    if max_right < min_left or max_bottom < min_top:
        return 0

    width = max_right - min_left
    height = max_bottom - min_top
    return width * height


def _common_interval_length(
    i1_start: int, i1_end: int, i2_start: int, i2_end: int
) -> int:
    """Calculates the length of the overlap between two 1D intervals.

    Args:
        i1_start: Start of the first interval.
        i1_end: End of the first interval.
        i2_start: Start of the second interval.
        i2_end: End of the second interval.

    Returns:
        The length of the common interval. Returns 0 if there is no overlap.
    """
    if i1_end < i2_start or i2_end < i1_start:
        return 0
    return min(i1_end, i2_end) - max(i1_start, i2_start)


class MaxRectsBinPacker:
    """Implements the MaxRects algorithm for packing rectangles into a single bin.

    This packer attempts to fit a list of rectangles (images) into a bin of
    dynamically adjusting size, trying different heuristics to find an optimal
    arrangement that minimizes wasted space.

    Attributes:
        verbose: If True, prints debug information during packing.
        padding: Internal padding for each rectangle.
        margin: Space between packed rectangles.
        padding_both_sides: Total padding added to width/height (padding * 2).
        bin_width: Current width of the packing bin.
        bin_height: Current height of the packing bin.
        score1: Primary score used by heuristics for ranking placements.
        score2: Secondary score used by heuristics for tiebreaking.
        surface_area: Total area of all source rectangles to be packed.
        used_rectangles: List of `Rectangle` objects successfully placed.
        free_rectangles: List of `Rectangle` objects representing free spaces in the bin.
        heuristic: The current packing heuristic being used.
    """

    def __init__(
        self, margin: int = 0, padding: int = 0, verbose: bool = False
    ):
        """Initializes the MaxRectsBinPacker.

        Args:
            margin: The space between packed rectangles. Defaults to 0.
            padding: The internal padding for each rectangle. Defaults to 0.
            verbose: If True, prints debug information. Defaults to False.
        """
        self.verbose = verbose

        self.padding = max(0, min(int(padding), MAX_PADDING))
        self.margin = max(0, min(int(margin), MAX_MARGIN))

        self.padding_both_sides = self.padding * 2

        self.bin_width = 2
        self.bin_height = 2
        self.score1 = 0.0
        self.score2 = 0.0

        self.surface_area = 0

        self.used_rectangles = []
        self.free_rectangles = []

        self._source_list_orig = []
        self.source_list_current_attempt = []

        self._current_arrangement_by_heuristic_kv = {}

        self.min_width_request = 0.0
        self.min_height_request = 0.0
        self.min_area_request = 0.0

        self.heuristic = ""
        self.heuristic_ring = {}  # Will be set to HEURISTIC_RING_SINGLE_BIN
        self.start_time = 0.0

        self._final_result_payload = None
        self._packing_error_message = None
        self._input_images_data_copy = {}

    def pack(self, images: Dict) -> Dict:  # noqa: PLR0912
        """Packs the given images into a single bin.

        The method processes a dictionary of image data, prepares rectangles
        (adding padding), and then attempts to pack them using various heuristics.
        It updates the input `images_data` dictionary with placement information
        ('fit' key) for each image.

        Args:
            images: Dictionary of materials and their image/size data.
                    Each item should have the format:
                    {material_id: {'gfx': {'size': (width, height)}}}

        Returns:
            The updated bin dictionary with position information in each item's
            'gfx.fit' field, containing x, y coordinates, width and height.

        Raises:
            PackingError: If input data is invalid, no valid rectangles can be
                formed, or if the packing process fails to find a suitable
                arrangement (e.g., exceeds max bin size).
        """
        self._input_images_data_copy = {k: v for k, v in images.items()}

        source_rects_prepared = []
        for img_id, data in images.items():
            try:
                size = data["gfx"]["size"]
                original_width, original_height = int(size[0]), int(size[1])
            except (KeyError, IndexError, TypeError, ValueError) as e:
                raise PackingError(
                    "Invalid image data format for '{}': {}".format(img_id, e)
                ) from e

            if not (original_width > 0 and original_height > 0):
                raise PackingError(
                    "Image '{}' has non-positive dimensions: ({}x{})".format(
                        img_id, original_width, original_height
                    )
                )

            current_width = original_width + self.padding_both_sides
            current_height = original_height + self.padding_both_sides

            source_rects_prepared.append(
                {
                    "id": img_id,
                    "width": current_width,
                    "height": current_height,
                    "area": current_width * current_height,
                    "original_width": original_width,
                    "original_height": original_height,
                }
            )

        if not source_rects_prepared:
            if not images:  # If input was empty, return empty.
                return {}
            raise PackingError(
                "No valid rectangles to pack from the input images_data."
            )

        self._source_list_orig = source_rects_prepared

        self.heuristic_ring = HEURISTIC_RING_SINGLE_BIN  # Explicitly single bin
        self.heuristic = HEURISTIC_BEST_SHORT_SIDE_FIT

        self.start_time = time.perf_counter()
        self._current_arrangement_by_heuristic_kv = {}
        self._final_result_payload = None
        self._packing_error_message = None

        try:
            self._start_calculation_from_min_bin_size()
        except PackingError as e:
            self._packing_error_message = str(e)

        if self._packing_error_message:
            raise PackingError(self._packing_error_message)

        if self._final_result_payload is None or not isinstance(
            self._final_result_payload, dict
        ):
            raise PackingError(
                "Packing process finished without a valid result. Max bin size might have been "
                "exceeded for all heuristics, or no valid arrangement found."
            )

        final_arrangement_snapshot = self._final_result_payload

        output_dict_to_return = self._input_images_data_copy

        placed_rect_ids = set()
        if "arrangement" in final_arrangement_snapshot:
            for rect_obj in final_arrangement_snapshot["arrangement"]:
                rect_id = rect_obj.id
                placed_rect_ids.add(rect_id)
                if rect_id in output_dict_to_return:
                    if "gfx" not in output_dict_to_return[rect_id]:
                        output_dict_to_return[rect_id]["gfx"] = {}

                    output_dict_to_return[rect_id]["gfx"]["fit"] = {
                        "x": rect_obj.left,
                        "y": rect_obj.top,
                        "w": rect_obj.width,
                        "h": rect_obj.height,
                    }
                elif self.verbose:
                    print(
                        "Warning: Placed rectangle with ID '{}' not found in original input data structure.".format(
                            rect_id
                        )
                    )

        return output_dict_to_return

    def _start_calculation_from_min_bin_size(self) -> None:
        """Initializes bin size and starts the packing calculation.

        Calculates an initial bin size based on the total surface area of
        rectangles and then calls `_start_calculation`.
        """
        if self.verbose:
            print(
                "[_start_calculation_from_min_bin_size] heuristic:{}".format(
                    self.heuristic
                )
            )

        self.surface_area = _calc_surface_area(self._source_list_orig)

        min_size = 2
        # Determine a reasonable starting bin dimension (power of 2)
        # that can hold the total surface area.
        while (
            min_size * min_size < self.surface_area
            and min_size
            <= MAX_BIN_WIDTH / 2  # Avoid excessively large initial sizes.
        ):
            min_size <<= 1

        min_size = min(min_size, MAX_BIN_WIDTH, MAX_BIN_HEIGHT)

        if self.verbose:
            print(
                "[pack] surface_area:{} (sqrt:{}), initial min_size:{}".format(
                    self.surface_area,
                    math.ceil(math.sqrt(self.surface_area)),
                    min_size,
                )
            )

        self.bin_width = min_size
        self.bin_height = min_size
        self._start_calculation()

    def _expend_bin_size(self) -> None:
        """Increases bin size and restarts calculation or tries the next heuristic.

        If the new size is within limits, `_start_calculation` is called.
        Otherwise, the current heuristic is marked as failed, and
        `_use_next_heuristic` is called.
        """
        new_w = self.bin_width + 32
        new_h = self.bin_height + 32

        if self.verbose:
            print(
                "[_expend_bin_size] from {}x{} to {}x{}".format(
                    self.bin_width, self.bin_height, new_w, new_h
                )
            )

        if new_w <= MAX_BIN_WIDTH and new_h <= MAX_BIN_HEIGHT:
            self.bin_width = new_w
            self.bin_height = new_h
            self._start_calculation()
        else:
            # Mark the current heuristic as failed for this bin size path.
            self._current_arrangement_by_heuristic_kv[self.heuristic] = (
                CALCULATION_FAILED
            )
            self._use_next_heuristic()

    def _pick_arrangement(self) -> Optional[Dict[str, Any]]:
        """Selects the best arrangement from successful heuristic attempts.

        Compares arrangements based on their 'occupied_area'.

        Returns:
            A dictionary representing the best arrangement found, or None if
            no suitable arrangement was found across all heuristics.
        """
        best_arrangement = None

        for (
            heuristic_name_attempted
        ) in self._current_arrangement_by_heuristic_kv:
            arrangement_result = self._current_arrangement_by_heuristic_kv[
                heuristic_name_attempted
            ]

            if arrangement_result == CALCULATION_FAILED or not isinstance(
                arrangement_result, dict
            ):
                continue

            if "occupied_area" not in arrangement_result:
                if self.verbose:
                    print(
                        "Warning: Arrangement for {} missing 'occupied_area'. Skipping.".format(
                            heuristic_name_attempted
                        )
                    )
                continue

            if self.verbose:
                print(
                    "[_pick_arrangement] Considering heuristic:{}, occupied_area:{}".format(
                        arrangement_result.get("heuristic"),
                        arrangement_result["occupied_area"],
                    )
                )

            if best_arrangement is None:
                best_arrangement = arrangement_result
            elif (
                "occupied_area" in best_arrangement  # Ensure the key exists
                and arrangement_result["occupied_area"]
                < best_arrangement["occupied_area"]
            ):
                best_arrangement = arrangement_result

        if best_arrangement and self.verbose:
            print(
                "[_pick_arrangement] BEST: heuristic:{}, occupied_area:{}".format(
                    best_arrangement.get("heuristic"),
                    best_arrangement.get("occupied_area"),
                )
            )
        elif not best_arrangement and self.verbose:
            print("[_pick_arrangement] No suitable arrangement found.")

        return best_arrangement

    def _take_snapshot(self) -> Dict[str, Any]:
        """Creates a snapshot of the current packing state.

        This includes metrics like occupied area, plot ratio, and the
        arrangement of used rectangles.

        Returns:
            A dictionary containing the snapshot of the current packing state.
        """
        surface_area_placed = 0
        for r in self.used_rectangles:
            # Find original dimensions to calculate the true surface area placed,
            # excluding padding for this metric.
            original_rect_data = next(
                (item for item in self._source_list_orig if item["id"] == r.id),
                None,
            )
            if original_rect_data:
                surface_area_placed += (
                    original_rect_data["original_width"]
                    * original_rect_data["original_height"]
                )
            else:
                # Fallback if original data not found (should not happen in normal flow).
                surface_area_placed += (
                    r.width * r.height
                )  # This would include padding.

        occupied_area = _calc_occupied_area(
            self.used_rectangles, self.bin_width, self.bin_height
        )

        plot_ratio = 0
        if self.bin_width * self.bin_height > 0:
            plot_ratio = surface_area_placed / (
                self.bin_width * self.bin_height
            )

        snapshot = {
            # Area of actual images, no padding
            "surface_area": surface_area_placed,
            # Bounding box area of placed padded rects
            "occupied_area": occupied_area,
            "bin_width": self.bin_width,
            "bin_height": self.bin_height,
            # List of Rectangle objects
            "arrangement": [r for r in self.used_rectangles],
            "heuristic": self.heuristic,
            "free_rects_count": len(self.free_rectangles),
            # Ratio of image surface to bin area
            "plot_ratio": plot_ratio,
            "time_spent_ms": (time.perf_counter() - self.start_time) * 1000,
        }
        # Reset for the next snapshot or phase
        self.start_time = time.perf_counter()
        return snapshot

    def _use_next_heuristic(self) -> None:
        """Switches to the next heuristic in the predefined ring.

        If all heuristics have been tried, call `_complete`. Otherwise,
        restarts the packing process from the minimum bin size with the
        new heuristic.
        """
        next_heuristic = self.heuristic_ring.get(self.heuristic)
        if self.verbose:
            print(
                "[_use_next_heuristic] Current: {}, Next: {}".format(
                    self.heuristic, next_heuristic
                )
            )

        if next_heuristic is None:
            self._complete()  # All heuristics in the ring attempted.
        else:
            self.heuristic = next_heuristic
            self._start_calculation_from_min_bin_size()

    def _complete(self) -> None:
        """Finalizes the packing process.

        Picks the best arrangement found, applies de-padding if necessary,
        and sets the final result payload. If no suitable arrangement is found,
        sets an error message.
        """
        if self.verbose:
            print("[_complete] All heuristics attempted or process finalized.")

        best_arrangement_snapshot = self._pick_arrangement()

        if best_arrangement_snapshot is None:
            err_msg = (
                "Overall packing failed. Max texture size allowed: "
                "{}x{}. No suitable arrangement found.".format(
                    MAX_BIN_WIDTH, MAX_BIN_HEIGHT
                )
            )
            if self.verbose:
                print("[_complete] {}".format(err_msg))
            self._packing_error_message = err_msg
            return  # Exit early if no arrangement found

        # If padding was used, shrink the placed rectangles back to the original size.
        if self.padding > 0:
            if "arrangement" in best_arrangement_snapshot and isinstance(
                best_arrangement_snapshot["arrangement"], list
            ):
                for rect_obj in best_arrangement_snapshot["arrangement"]:
                    if isinstance(rect_obj, Rectangle):
                        rect_obj.shrink(self.padding)
            elif self.verbose:
                print(
                    "Warning: 'arrangement' key missing or invalid in best_arrangement_snapshot during de-padding."
                )

        self._final_result_payload = best_arrangement_snapshot

        if self.verbose:
            print(
                "[_complete] Successfully generated arrangement with heuristic: {}".format(
                    best_arrangement_snapshot.get("heuristic")
                )
            )

    def _start_calculation(self) -> None:
        """Resets state and starts a packing attempt for the current bin size and heuristic.

        Initializes `used_rectangles` and `free_rectangles`, and copies
        the original list of rectangles to `source_list_current_attempt`.
        Then calls `_calc_each_rect_iterative`.
        """
        if self.verbose:
            print(
                "[_start_calculation] Heuristic:{}, BinSize:{}x{}".format(
                    self.heuristic, self.bin_width, self.bin_height
                )
            )

        self.used_rectangles = []
        # Initialize free space with a single rectangle covering the entire bin.
        self.free_rectangles = [
            Rectangle(0, 0, self.bin_width, self.bin_height, "bin_root")
        ]

        # Create a fresh copy of source rectangles for this attempt.
        self.source_list_current_attempt = [
            dict(r) for r in self._source_list_orig
        ]

        self._calc_each_rect_iterative()

    def _calc_each_rect_iterative(self) -> None:  # noqa: PLR0912
        """Iteratively attempts to place each source rectangle.

        In each iteration, it finds the best position for the "best" fitting
        rectangle from the remaining source list based on the current heuristic.
        If a rectangle cannot be placed, the bin size is expanded.
        If all rectangles are placed, the current arrangement is snapshotted,
        and the next heuristic is tried.
        """
        while True:
            # Loop until all rects placed or bin expansion/heuristic change.
            if not self.source_list_current_attempt:
                # All rectangles for the current attempt have been placed.
                if self.verbose:
                    print(
                        "[_calc_each_rect_iterative] All source rects placed for {}.".format(
                            self.heuristic
                        )
                    )
                self._current_arrangement_by_heuristic_kv[self.heuristic] = (
                    self._take_snapshot()
                )
                self._use_next_heuristic()  # Try the next heuristic or complete.
                return

            if self.verbose:
                print(
                    "[_calc_each_rect_iterative] Heuristic:{}, Progress: {}/{}, Remaining: {}".format(
                        self.heuristic,
                        len(self.used_rectangles),
                        len(self._source_list_orig),
                        len(self.source_list_current_attempt),
                    )
                )

            best_score1_for_iter = float("inf")
            best_score2_for_iter = float("inf")
            # Index in source_list_current_attempt
            best_original_rect_index = -1
            best_placed_rect_candidate = None

            # Determine minimum dimensions required by remaining free rectangles
            # for pruning the free list effectively.
            self.min_width_request = float("inf")
            self.min_height_request = float("inf")
            self.min_area_request = float("inf")
            if self.source_list_current_attempt:
                for r_data in self.source_list_current_attempt:
                    self.min_width_request = min(
                        self.min_width_request, r_data["width"]
                    )
                    self.min_height_request = min(
                        self.min_height_request, r_data["height"]
                    )
                    self.min_area_request = min(
                        self.min_area_request, r_data["area"]
                    )
            else:  # Should not happen if the loop condition `not self.source_list_current_attempt` is met.
                # Defensive default values.
                self.min_width_request = 1
                self.min_height_request = 1
                self.min_area_request = 1

            # Find the best rectangle to place in this iteration.
            for i, rect_data_from_source in enumerate(
                self.source_list_current_attempt
            ):
                potential_placement = self._score_rect(rect_data_from_source)

                if (
                    potential_placement is None
                ):  # Cannot place this specific rect.
                    # This means no free node can fit it with the current heuristic.
                    if self.verbose:
                        print(
                            "[_calc_each_rect_iterative] Cannot place rect {}. Expanding bin.".format(
                                rect_data_from_source["id"]
                            )
                        )
                    self._expend_bin_size()  # Expand and retry for all rects.
                    return

                # Check if this placement is better than the previous best for this iteration.
                if self.score1 < best_score1_for_iter or (
                    self.score1 == best_score1_for_iter
                    and self.score2 < best_score2_for_iter
                ):
                    best_score1_for_iter = self.score1
                    best_score2_for_iter = self.score2
                    best_placed_rect_candidate = potential_placement
                    best_original_rect_index = i

            if best_placed_rect_candidate is None:
                # This case implies that for ALL remaining rects, _score_rect found a place,
                # but something went wrong, or no rects were scorable.
                # This usually indicates a need to expand the bin.
                if self.source_list_current_attempt and self.verbose:
                    print(
                        "Warning: No best candidate found in _calc_each_rect_iterative "
                        "despite source list having {} items. Expanding bin.".format(
                            len(self.source_list_current_attempt)
                        )
                    )
                self._expend_bin_size()
                return

            # Place the chosen best rectangle.
            self._place_rect(best_placed_rect_candidate)
            self.source_list_current_attempt.pop(best_original_rect_index)
            self._prune_free_list()  # Clean up a free list after placement.

    def _place_rect(self, rect_to_place: Rectangle) -> None:
        """Places a rectangle and updates the free rectangles list.

        Iterates through the `free_rectangles` list, and for each free node
        that intersects with `rect_to_place`, it calls `_split_free_node`
        to potentially divide the free node into smaller pieces.

        Args:
            rect_to_place: The `Rectangle` object to be placed.
        """
        if self.verbose:
            print(
                "[_place_rect] Placing: {}, FreeRects before split: {}".format(
                    rect_to_place, len(self.free_rectangles)
                )
            )

        num_free_rects_before = len(self.free_rectangles)
        i = 0
        while i < len(self.free_rectangles):
            if self._split_free_node(self.free_rectangles[i], rect_to_place):
                # If split_free_node returns True, it means the free_rectangles[i]
                # was split and/or fully consumed by used_node.
                # The original free_rectangles[i] is now invalid and should be removed.
                # Split_free_node might have added new smaller free rectangles.
                self.free_rectangles.pop(i)
                # Do not increment i, as the list has shifted.
            else:
                i += 1  # The current free_node was not affected, move to the next.

        if self.verbose:
            print(
                "[_place_rect] FreeRects after split: {}; Change: {}".format(
                    len(self.free_rectangles),
                    len(self.free_rectangles) - num_free_rects_before,
                )
            )

        self.used_rectangles.append(rect_to_place)

    def _split_free_node(
        self, free_node: Rectangle, used_node: Rectangle
    ) -> bool:
        """Splits a free rectangle based on an overlapping used rectangle.

        If `used_node` overlaps with `free_node`, `free_node` is divided into
        up to four new smaller free rectangles around `used_node`.
        New free rectangles are only added if they meet minimum size requirements.

        Args:
            free_node: The free `Rectangle` to potentially split.
            used_node: The `Rectangle` that has been placed and is causing the split.

        Returns:
            True if `free_node` overlaps with `used_node` (and was thus processed
            for splitting), False otherwise (no overlap).
        """
        # Check if the two rectangles overlap at all.
        if (
            used_node.left >= free_node.right
            or used_node.right <= free_node.left
            or used_node.top >= free_node.bottom
            or used_node.bottom <= free_node.top
        ):
            return False  # No overlap, free_node remains untouched by this used_node.

        # New free rectangle above the used_node.
        if (
            free_node.top < used_node.top < free_node.bottom
        ):  # Check avoids creating zero-height rects at edges
            change_h = used_node.top - free_node.top - self.margin
            if (
                change_h
                >= self.min_height_request  # Check if the new rect is large enough
                and free_node.width * change_h >= self.min_area_request
            ):
                self.free_rectangles.append(
                    Rectangle(
                        free_node.left,
                        free_node.top,
                        free_node.width,
                        change_h,
                        "f_split_top",
                    )
                )

        # New free rectangle below the used_node.
        if (
            used_node.bottom < free_node.bottom
        ):  # Check avoids creating zero-height rects at edges
            change_h = free_node.bottom - used_node.bottom - self.margin
            if (
                change_h >= self.min_height_request
                and free_node.width * change_h >= self.min_area_request
            ):
                self.free_rectangles.append(
                    Rectangle(
                        free_node.left,
                        used_node.bottom + self.margin,
                        free_node.width,
                        change_h,
                        "f_split_bottom",
                    )
                )

        # New free rectangle to the left of the used_node.
        if (
            free_node.left < used_node.left < free_node.right
        ):  # Check avoids creating zero-width rects at edges
            change_w = used_node.left - free_node.left - self.margin
            if (
                change_w >= self.min_width_request
                and change_w * free_node.height >= self.min_area_request
            ):
                self.free_rectangles.append(
                    Rectangle(
                        free_node.left,
                        free_node.top,
                        change_w,
                        free_node.height,
                        "f_split_left",
                    )
                )

        # New free rectangle to the right of the used_node.
        if (
            used_node.right < free_node.right
        ):  # Check avoids creating zero-width rects at edges
            change_w = free_node.right - used_node.right - self.margin
            if (
                change_w >= self.min_width_request
                and change_w * free_node.height >= self.min_area_request
            ):
                self.free_rectangles.append(
                    Rectangle(
                        used_node.right + self.margin,
                        free_node.top,
                        change_w,
                        free_node.height,
                        "f_split_right",
                    )
                )

        return True  # free_node was overlapped and processed.

    def _score_rect(self, rect_data: Dict[str, Any]) -> Optional[Rectangle]:
        """Scores a rectangle placement based on the current heuristic.

        Calls the appropriate `_find_position_*` method for the active
        heuristic. Sets `self.score1` and `self.score2` based on the heuristic's
        criteria.

        Args:
            rect_data: Dictionary containing 'id', 'width', and 'height' of the
                rectangle to score.

        Returns:
            A `Rectangle` object representing the best found placement if one
            exists, otherwise None. `self.score1` and `self.score2` are updated
            by the called heuristic find method.
        """
        rect_id = rect_data["id"]
        width = rect_data["width"]
        height = rect_data["height"]

        self.score1 = float("inf")  # Initialize scores for this attempt.
        self.score2 = float("inf")

        if self.heuristic == HEURISTIC_BEST_SHORT_SIDE_FIT:
            placed_node = self._find_position_bssf(rect_id, width, height)
        elif self.heuristic == HEURISTIC_BEST_LONG_SIDE_FIT:
            placed_node = self._find_position_blsf(rect_id, width, height)
        elif self.heuristic == HEURISTIC_BEST_AREA_FIT:
            placed_node = self._find_position_baf(rect_id, width, height)
        elif self.heuristic == HEURISTIC_BOTTOM_LEFT_RULE:
            placed_node = self._find_position_bl(rect_id, width, height)
        elif self.heuristic == HEURISTIC_CONTACT_POINT_RULE:
            placed_node = self._find_position_cp(rect_id, width, height)
            # For CP, a higher score is better, so we negate it here if score1 was set.
            # The _find_position_cp method sets score1 directly to the contact score.
            if placed_node:  # Check if a node was actually found
                # Score1 already holds the contact score; comparison logic expects lower is better.
                # To make a higher contact score "better" in a min-comparison framework,
                # we could use -contact_score.
                # However, the logic in _calc_each_rect_iterative expects:
                # if self.score1 < best_score1_for_iter...
                # The original code `self.score1 = -self.score1` flips it.
                # This implies score1 from _find_position_cp is positive.
                self.score1 = (
                    -self.score1
                )  # Invert for comparison (higher contact points are better)
        else:
            if self.verbose:
                print("Warning: Unknown heuristic: {}".format(self.heuristic))
            return None  # Should not happen with defined heuristics.

        # If no node was placed, or it has zero height (effectively not placed).
        if placed_node is None or placed_node.height == 0:
            self.score1 = float("inf")  # Ensure it's a bad score.
            self.score2 = float("inf")
            return None

        return placed_node

    def _find_position_bssf(
        self, rect_id: str, width: int, height: int
    ) -> Optional[Rectangle]:
        """Finds the best position for a rectangle using Best Short Side Fit.

        Tries to place the rectangle `width`x`height` in a free spot such that
        the shorter of the leftover sides (horizontal or vertical) is minimized.
        If ties, minimizes the longer leftover side. Updates `self.score1` and
        `self.score2`.

        Args:
            rect_id: Identifier for the rectangle.
            width: Width of the rectangle to place.
            height: Height of the rectangle to place.

        Returns:
            A `Rectangle` object representing the best position, or None if
            no suitable position is found.
        """
        best_node_found = None
        current_best_short_side_fit = float("inf")  # Score1
        current_best_long_side_fit = float("inf")  # Score2

        for free_rect in self.free_rectangles:
            if free_rect.width >= width and free_rect.height >= height:
                leftover_horiz = free_rect.width - width
                leftover_vert = free_rect.height - height

                short_side_fit = min(leftover_horiz, leftover_vert)
                long_side_fit = max(leftover_horiz, leftover_vert)

                if short_side_fit < current_best_short_side_fit or (
                    short_side_fit == current_best_short_side_fit
                    and long_side_fit < current_best_long_side_fit
                ):
                    current_best_short_side_fit = short_side_fit
                    current_best_long_side_fit = long_side_fit
                    if best_node_found is None:
                        best_node_found = Rectangle(
                            free_rect.left,
                            free_rect.top,
                            width,
                            height,
                            rect_id,
                        )
                    else:
                        # Reuse existing Rectangle object to avoid frequent allocations.
                        best_node_found.reset(
                            free_rect.left, free_rect.top, width, height
                        )

        if best_node_found:
            self.score1 = current_best_short_side_fit
            self.score2 = current_best_long_side_fit
        return best_node_found

    def _find_position_blsf(
        self, rect_id: str, width: int, height: int
    ) -> Optional[Rectangle]:
        """Finds the best position for a rectangle using Best Long Side Fit.

        Tries to place the rectangle `width`x`height` in a free spot such that
        the longer of the leftover sides (horizontal or vertical) is minimized.
        If ties, minimizes the shorter leftover side. Updates `self.score1` and
        `self.score2`.

        Args:
            rect_id: Identifier for the rectangle.
            width: Width of the rectangle to place.
            height: Height of the rectangle to place.

        Returns:
            A `Rectangle` object representing the best position, or None if
            no suitable position is found.
        """
        best_node_found = None
        current_best_short_side_fit = float("inf")  # Score2
        current_best_long_side_fit = float("inf")  # Score1

        for free_rect in self.free_rectangles:
            if free_rect.width >= width and free_rect.height >= height:
                leftover_horiz = free_rect.width - width
                leftover_vert = free_rect.height - height

                short_side_fit = min(leftover_horiz, leftover_vert)
                long_side_fit = max(leftover_horiz, leftover_vert)

                # Note: Original code had score1=short, score2=long for BLSF,
                # but logic implies score1=long, score2=short.
                # The comparison `long_side_fit < current_best_long_side_fit`
                # means long_side_fit is primary.
                if long_side_fit < current_best_long_side_fit or (
                    long_side_fit == current_best_long_side_fit
                    and short_side_fit < current_best_short_side_fit
                ):
                    current_best_long_side_fit = long_side_fit
                    current_best_short_side_fit = short_side_fit
                    if best_node_found is None:
                        best_node_found = Rectangle(
                            free_rect.left,
                            free_rect.top,
                            width,
                            height,
                            rect_id,
                        )
                    else:
                        best_node_found.reset(
                            free_rect.left, free_rect.top, width, height
                        )

        if best_node_found:
            self.score1 = current_best_long_side_fit
            self.score2 = current_best_short_side_fit
        return best_node_found

    def _find_position_baf(
        self, rect_id: str, width: int, height: int
    ) -> Optional[Rectangle]:
        """Finds the best position for a rectangle using Best Area Fit.

        Tries to place the rectangle `width`x`height` in a free spot such that
        the remaining area in the chosen free spot is minimized.
        If ties, minimizes the shorter leftover side. Updates `self.score1` and
        `self.score2`.

        Args:
            rect_id: Identifier for the rectangle.
            width: Width of the rectangle to place.
            height: Height of the rectangle to place.

        Returns:
            A `Rectangle` object representing the best position, or None if
            no suitable position is found.
        """
        best_node_found = None
        current_best_area_fit = float("inf")  # Score1
        current_best_short_side_fit = float("inf")  # Score2
        request_area = width * height

        for free_rect in self.free_rectangles:
            if free_rect.width >= width and free_rect.height >= height:
                leftover_horiz = free_rect.width - width
                leftover_vert = free_rect.height - height

                area_fit = (
                    free_rect.area - request_area
                )  # Remaining area in this free_rect
                short_side_fit = min(leftover_horiz, leftover_vert)

                if area_fit < current_best_area_fit or (
                    area_fit == current_best_area_fit
                    and short_side_fit < current_best_short_side_fit
                ):
                    current_best_area_fit = area_fit
                    current_best_short_side_fit = short_side_fit
                    if best_node_found is None:
                        best_node_found = Rectangle(
                            free_rect.left,
                            free_rect.top,
                            width,
                            height,
                            rect_id,
                        )
                    else:
                        best_node_found.reset(
                            free_rect.left, free_rect.top, width, height
                        )

        if best_node_found:
            self.score1 = current_best_area_fit
            self.score2 = current_best_short_side_fit
        return best_node_found

    def _find_position_bl(
        self, rect_id: str, width: int, height: int
    ) -> Optional[Rectangle]:
        """Finds the best position for a rectangle using the Bottom-Left rule.

        Places the rectangle at the lowest, then leftmost, available position.
        `self.score1` becomes the y-coordinate of the bottom edge of the placed
        rectangle, and `self.score2` becomes the x-coordinate of its left edge.

        Args:
            rect_id: Identifier for the rectangle.
            width: Width of the rectangle to place.
            height: Height of the rectangle to place.

        Returns:
            A `Rectangle` object representing the best position, or None if
            no suitable position is found.
        """
        best_node_found = None
        current_best_y = float("inf")  # Score1 (bottom edge y-coordinate)
        current_best_x = float("inf")  # Score2 (left edge x-coordinate)

        for free_rect in self.free_rectangles:
            if free_rect.width >= width and free_rect.height >= height:
                # Score by the bottom-most coordinate first, then left-most.
                # Score1_candidate is effectively free_rect.bottom if rect is placed at free_rect.top
                score1_candidate = (
                    free_rect.top + height
                )  # Bottom edge of potential placement
                score2_candidate = (
                    free_rect.left
                )  # Left edge of potential placement

                if score1_candidate < current_best_y or (
                    score1_candidate == current_best_y
                    and score2_candidate < current_best_x
                ):
                    current_best_y = score1_candidate
                    current_best_x = score2_candidate
                    if best_node_found is None:
                        best_node_found = Rectangle(
                            free_rect.left,
                            free_rect.top,
                            width,
                            height,
                            rect_id,
                        )
                    else:
                        best_node_found.reset(
                            free_rect.left, free_rect.top, width, height
                        )

        if best_node_found:
            self.score1 = current_best_y
            self.score2 = current_best_x
        return best_node_found

    def _find_position_cp(
        self, rect_id: str, width: int, height: int
    ) -> Optional[Rectangle]:
        """Finds the best position using Contact Point heuristic.

        Places the rectangle to maximize the contact points with already
        placed rectangles or bin boundaries. `self.score1` is set to the
        contact score (higher is better). `self.score2` is unused.

        Args:
            rect_id: Identifier for the rectangle.
            width: Width of the rectangle to place.
            height: Height of the rectangle to place.

        Returns:
            A `Rectangle` object representing the best position, or None if
            no suitable position is found.
        """
        best_node_found = None
        best_contact_score = -1  # Higher is better, so start with a low value.

        for free_rect in self.free_rectangles:
            if free_rect.width >= width and free_rect.height >= height:
                # Try placing at the top-left of the free_rect.
                contact_score = self._contact_point_score_node(
                    free_rect.left, free_rect.top, width, height
                )

                if contact_score > best_contact_score:
                    best_contact_score = contact_score
                    if best_node_found is None:
                        best_node_found = Rectangle(
                            free_rect.left,
                            free_rect.top,
                            width,
                            height,
                            rect_id,
                        )
                    else:
                        best_node_found.reset(
                            free_rect.left, free_rect.top, width, height
                        )
        # Note: score1 for CP heuristic is handled in _score_rect where it's negated
        # because the main comparison logic assumes lower scores are better.
        # Here, we just set score1 to the raw contact score.
        if best_node_found:
            self.score1 = (
                best_contact_score  # Raw contact score (higher is better)
            )
            self.score2 = (
                0  # Not used by CP heuristic for tiebreaking in this impl.
            )
        return best_node_found

    def _contact_point_score_node(
        self, left: int, top: int, width: int, height: int
    ) -> int:
        """Calculates the contact point score for a potential placement.

        The score is the sum of lengths of edges that touch other placed
        rectangles or the bin boundaries.

        Args:
            left: The left x-coordinate of the potential placement.
            top: The top y-coordinate of the potential placement.
            width: The width of the rectangle being placed.
            height: The height of the rectangle being placed.

        Returns:
            The contact point score.
        """
        score = 0
        right = left + width
        bottom = top + height

        # Contact with bin boundaries
        if left == 0 or right == self.bin_width:
            score += height
        if top == 0 or bottom == self.bin_height:
            score += width

        # Contact with other used rectangles
        for rect in self.used_rectangles:
            # Check for vertical adjacency (sharing a vertical edge)
            if rect.left == right or rect.right == left:
                score += _common_interval_length(
                    rect.top, rect.bottom, top, bottom
                )
            # Check for horizontal adjacency (sharing a horizontal edge)
            if rect.top == bottom or rect.bottom == top:
                score += _common_interval_length(
                    rect.left, rect.right, left, right
                )
        return score

    def _prune_free_list(self) -> None:  # noqa: PLR0912
        """Removes redundant or too-small free rectangles.

        Performs two passes:
        1. Filters out free rectangles that are smaller than the minimum
           dimensions required by any remaining source rectangle.
        2. Filters out free rectangles that are entirely contained within
           another free rectangle in the list.
        """
        if self.verbose:
            print(
                "[_prune_free_list] Count before: {}, min_w_req:{}, min_h_req:{}, min_area_req:{}".format(
                    len(self.free_rectangles),
                    self.min_width_request,
                    self.min_height_request,
                    self.min_area_request,
                )
            )

        # Pass 1: Filter out rectangles that are too small to hold any remaining source rectangle.
        survivors_pass1 = []
        for fr in self.free_rectangles:
            is_too_small = False
            # Check against valid (non-infinite) minimum requests.
            # These min_width/height/area_request are updated in _calc_each_rect_iterative
            # based on the smallest remaining source rectangles.
            if (
                self.min_width_request
                != float("inf")  # Ensure valid comparison
                and fr.width < self.min_width_request
            ):
                is_too_small = True
            if (
                not is_too_small
                and self.min_height_request != float("inf")
                and fr.height < self.min_height_request
            ):
                is_too_small = True
            if (
                not is_too_small
                and self.min_area_request != float("inf")
                and fr.area < self.min_area_request
            ):
                is_too_small = True

            if not is_too_small:
                survivors_pass1.append(fr)
            elif self.verbose:
                print(
                    "[_prune_free_list] Pruning small rect (pass 1): {}".format(
                        fr
                    )
                )

        # Pass 2: Filter out free rectangles that are contained by other free rectangles.
        # This means if rect_m contains rect_k, rect_k is redundant.
        final_free_rectangles = []
        for k_idx, rect_k in enumerate(survivors_pass1):
            is_contained_by_another = False
            for m_idx, rect_m in enumerate(survivors_pass1):
                if k_idx == m_idx:  # Don't compare a rectangle to itself.
                    continue
                if rect_m.contains(rect_k):
                    is_contained_by_another = True
                    if self.verbose:
                        print(
                            "[_prune_free_list] Pruning {} (contained by {}) (pass 2)".format(
                                rect_k, rect_m
                            )
                        )
                    break  # rect_k is contained, no need to check further.
            if not is_contained_by_another:
                final_free_rectangles.append(rect_k)

        self.free_rectangles = final_free_rectangles

        if self.verbose:
            print(
                "[_prune_free_list] Count after: {}".format(
                    len(self.free_rectangles)
                )
            )
