from bpy.app import version as blender_version

# Functions used to read/write pixel buffers from/to Images as fast as possible. These change based on the running
# Blender version as fast methods for accessing Image.pixels were only added in Blender 2.83.

# Setting both to None to start with and checking they are not None at the end isn't strictly necessary, but it makes it
# clearer to IDEs that the functions are used as opposed to ending this module with something like
# assert 'get_pixels' in globals() and 'set_pixels' in globals()
get_pixels = None
set_pixels = None

# get_pixels function
if blender_version >= (2, 83):  # bpy_prop_array.foreach_get was added in Blender 2.83
    # 1.6ms for 1024x1024
    # 15.2ms for 2048x2048
    # 60.9ms for 4096x4096
    # 306.2ms for 8192x8192
    from .fast_pixel_access_2_83_plus import get_pixels
elif blender_version >= (2, 80):  # Being able to use the memory of an existing buffer in bgl.Buffer was added in Blender 2.80, not that this behaviour is documented
    # TODO: Re-time to see if this really is slightly slower than get_pixels_ctypes_gl_buffer_swap
    # 16.7ms for 1024x1024
    # 65.9ms for 2048x2048
    # 293.9ms for 4096x4096
    # 1121.6ms for 8192x8192
    from .fast_pixel_read_2_80_to_2_82 import get_pixels_gl_shared_buffer as get_pixels
else:  # Oldest theoretically supported Blender version is 2.50, because that's when the bgl module was added
    try:
        # 9.7ms for 1024x1024
        # 52.7ms for 2048x2048
        # 201.8ms for 4096x4096
        # 818.8ms for 8192x8192
        from .fast_pixel_read_2_79 import get_pixels_ctypes_gl_buffer_swap as get_pixels
    except AssertionError:
        print("Failed to import fast_pixel_read_2_79, resorting to using much slower iteration to get image pixels from Open GL")
        # 159.6ms for 1024x1024
        # 636.5ms for 2048x2048
        # 2600.7ms for 4096x4096
        # 10215.1ms for 8192x8192
        from .fallback_pixel_access import get_pixels_gl_buffer_iter_2_79 as get_pixels

# set_pixels function
if blender_version >= (2, 83):
    # 7.6ms for 1024x1024
    # 29.6ms for 2048x2048
    # 114.7ms for 4096x4096
    # 471.5ms for 8192x8192
    from .fast_pixel_access_2_83_plus import set_pixels
else:
    try:
        # 7.8ms for 1024x1024
        # 35.7ms for 2048x2048
        # 135.8ms for 4096x4096
        # 701.7ms for 8192x8192
        from .fast_pixel_write_2_79_to_2_82 import set_pixels_matrix_hack as set_pixels
    except AssertionError:
        print("Failed to import ctypes_fast_pixel_write, resorting to much slower fallback method to set image pixels")
        # 85.5ms for 1024x1024
        # 388.2 for 2048x2048
        # 1511.1ms for 4096x4096
        # 6407.5ms for 8192x8192
        from .fallback_pixel_access import set_pixels_array_assign as set_pixels

assert get_pixels is not None
assert set_pixels is not None
