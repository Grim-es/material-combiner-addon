from typing import Dict
from typing import Iterable
from typing import List
from typing import cast

import bmesh


def get_loops(bm: bmesh.types.BMesh) -> Dict[bmesh.types.BMFace, List[bmesh.types.BMLoop]]:
    return {face: list(face.loops) for face in cast(Iterable, bm.faces)}
