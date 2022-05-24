import ctypes

# To help with understanding ctypes usage in this way, see:
# https://mcla.ug/blog/cpython-hackage.html
# https://github.com/CGCookie/addon_common/blob/b280/ext/bgl_ext.py

# This module sets up the basic Python types with ctypes, for use by other modules.


# Declare class to mirror PyObject type
# https://docs.python.org/3/c-api/structures.html#c.PyObject
# https://github.com/python/cpython/blob/10e5c66789a06dc9015a24968e96e77a75725a7a/Include/object.h#L104
class PyObject(ctypes.Structure):
    """typedef struct _object {
        _PyObject_HEAD_EXTRA
        Py_ssize_t ob_refcnt;
        struct _typeobject *ob_type;
    } PyObject;"""
    pass


# PyObject's Fields must be set separately as it references its own type
PyObject._fields_ = [
    ('ob_refcnt', ctypes.c_ssize_t),
    ('ob_type', ctypes.POINTER(PyObject)),
]

# _PyObject_HEAD_EXTRA expands out two extra fields sometimes
"""
#ifdef Py_TRACE_REFS
/* Define pointers to support a doubly-linked list of all live heap objects. */
#define _PyObject_HEAD_EXTRA            \\
    struct _object *_ob_next;           \\
    struct _object *_ob_prev;

#define _PyObject_EXTRA_INIT 0, 0,

#else
#define _PyObject_HEAD_EXTRA
#define _PyObject_EXTRA_INIT
#endif
"""
# Compare against object basicsize to check
if object.__basicsize__ != ctypes.sizeof(PyObject):
    # Remake the class with the extra fields (_fields_ cannot be modified after being set)
    class PyObject(ctypes.Structure):
        pass
    PyObject._fields_ = [
        ('_ob_next', ctypes.POINTER(PyObject)),
        ('_ob_prev', ctypes.POINTER(PyObject)),
        ('ob_refcnt', ctypes.c_ssize_t),
        ('ob_type', ctypes.POINTER(PyObject)),
    ]

# Ensure the size matches
assert object.__basicsize__ == ctypes.sizeof(PyObject)


# Declare class to mirror PyVarObject type
# https://docs.python.org/3/c-api/structures.html#c.PyVarObject
# https://github.com/python/cpython/blob/10e5c66789a06dc9015a24968e96e77a75725a7a/Include/object.h#L113
class PyVarObject(PyObject):
    """typedef struct {
        PyObject ob_base;
        Py_ssize_t ob_size; /* Number of items in variable part */
    } PyVarObject;"""
    _fields_ = [
        ('ob_size', ctypes.c_ssize_t),
    ]
