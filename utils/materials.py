"""Material processing utilities for Blender texture atlas generation.

This module provides robust material analysis and texture extraction for the
Material Combiner addon, supporting various shader systems including Principled
BSDF, MMD, MToon, VRM, and XNALara materials.
"""

from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Set, Tuple, ValuesView, cast

import bpy
import numpy as np

from .. import globs
from ..type_annotations import Diffuse, MatDict, MatDictItem
from .images import get_image, get_packed_file
from .textures import get_texture

# Color space conversion constants (sRGB)
GAMMA = 2.4
GAMMA_THRESHOLD = 0.0031308
LINEAR_FACTOR = 12.92
GAMMA_FACTOR = 1.055
GAMMA_OFFSET = 0.055
DEFAULT_DIFFUSE = (255, 255, 255, 255)

# Shader node type mappings
SHADER_NODE_TYPES = {
    "ShaderNodeBsdfPrincipled": "principled",
    "ShaderNodeBsdfDiffuse": "diffuse",
    "ShaderNodeEeveeSpecular": "specular",
    "ShaderNodeEmission": "emission",
    "ShaderNodeGroup": {
        "MToon_unversioned": "vrm",
        "XPS Shader": "xnalara",
        "Group": "xnalaraNew",
    },
}

# Shader-specific node names
MMD_SHADER_NODE = "mmd_shader"
MMD_TEXTURE_NODE = "mmd_base_tex"
MTOON_SHADER_NODE = "Mtoon1Material.Mtoon1Output"
MTOON_TEXTURE_NODE = "Mtoon1BaseColorTexture.Image"

# Shader type definitions with required nodes
SHADER_TYPES = OrderedDict(
    [
        ("mmd", {MMD_SHADER_NODE, MMD_TEXTURE_NODE}),
        ("mmdCol", {MMD_SHADER_NODE}),
        ("mtoon", {MTOON_TEXTURE_NODE}),
        ("mtoonCol", {MTOON_SHADER_NODE}),
        ("principled", {"Principled BSDF", "Image Texture"}),
        ("principledCol", {"Principled BSDF"}),
        ("diffuse", {"Diffuse BSDF", "Image Texture"}),
        ("diffuseCol", {"Diffuse BSDF"}),
        ("specular", {"Specular BSDF", "Image Texture"}),
        ("specularCol", {"Specular BSDF"}),
        ("emission", {"Emission", "Image Texture"}),
        ("emissionCol", {"Emission"}),
    ]
)

# Texture node mappings by shader type
SHADER_IMAGE_NODES = {
    "mmd": MMD_TEXTURE_NODE,
    "mtoon": MTOON_TEXTURE_NODE,
    "vrm": "Image Texture",
    "xnalara": "Image Texture",
    "principled": "Image Texture",
    "diffuse": "Image Texture",
    "specular": "Image Texture",
    "emission": "Image Texture",
}

# Albedo input names by shader type
SHADER_ALBEDO_INPUTS = {
    "principled": "Base Color",
    "diffuse": "Color",
    "specular": "Base Color",
    "emission": "Color",
    "mmd": "Diffuse Color",
    "mtoon": "Base Color",
    "vrm": "Color",
    "xnalara": "Diffuse",
    "xnalaraNew": "Diffuse",
}

# Common color input names across shader systems
COLOR_INPUT_NAMES = frozenset(
    ["Color", "Base Color", "Diffuse Color", "BaseColor"]
)

# Diffuse color accessors for color-only shaders
DIFFUSE_ACCESSORS = {
    "mmdCol": lambda n: n[MMD_SHADER_NODE]
    .inputs["Diffuse Color"]
    .default_value,
    "mtoonCol": lambda n: n["Mtoon1PbrMetallicRoughness.BaseColorFactor"].color,
    "vrm": lambda n: n["RGB"].outputs[0].default_value,
    "vrmCol": lambda n: n["Group"].inputs[10].default_value,
    "diffuseCol": lambda n: n["Diffuse BSDF"].inputs["Color"].default_value,
    "xnalaraNewCol": lambda n: n["Group"].inputs["Diffuse"].default_value,
    "principledCol": lambda n: n["Principled BSDF"]
    .inputs["Base Color"]
    .default_value,
    "xnalaraCol": lambda n: n["Principled BSDF"]
    .inputs["Base Color"]
    .default_value,
}

# Graphics texture input names by texture type for modern shaders
GFX_INPUT_NAMES = {
    "metallic": "Metallic",
    "roughness": "Roughness",
    "specular": "Specular Tint",
    "normal_map": "Normal",
    "emission": "Emission Color",
}

# Specular BSDF specific input names
SPECULAR_BSDF_INPUT_NAMES = {
    "roughness": "Roughness",
    "specular": "Specular",
    "normal_map": "Normal",
    "emission": "Emissive Color",
}


def get_materials(obj: bpy.types.Object) -> List[bpy.types.Material]:
    """Retrieves all valid materials from an object.

    Args:
        obj: Blender object to extract materials from.

    Returns:
        List of non-null materials assigned to the object.
    """
    return [
        slot.material
        for slot in obj.material_slots
        if slot.material is not None
    ]


def get_shader_type(mat: bpy.types.Material) -> Optional[str]:  # noqa: PLR0911
    """Identifies the shader type of material.

    Performs multi-stage detection:
    1. Connection-based detection from output node
    2. Group node detection for special cases
    3. Specific shader name matching
    4. Node name pattern matching

    Args:
        mat: Material to analyze.

    Returns:
        Shader type identifier or None if unrecognized.
        Types ending with 'Col' indicate color-only materials without textures.
    """
    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    nodes = mat.node_tree.nodes

    # Try connection-based detection first (most accurate)
    output_node = _find_output_node(nodes)
    if output_node:
        shader_info = _trace_shader_from_output(output_node)
        if shader_info:
            shader_node, shader_type = shader_info
            # Check for connected texture
            if _find_connected_image_node(shader_node, shader_type):
                return shader_type
            return "{}Col".format(shader_type)

    # Try group node detection
    shader_type = _detect_group_shader(nodes)
    if shader_type:
        return shader_type

    # Try specific shader detection
    node_names = set(nodes.keys())

    if {MMD_SHADER_NODE} & node_names:
        return "mmd" if {MMD_TEXTURE_NODE} & node_names else "mmdCol"

    if {MTOON_SHADER_NODE} & node_names:
        return "mtoon" if {MTOON_TEXTURE_NODE} & node_names else "mtoonCol"

    # Pattern-based detection as last resort
    for shader_type, required_nodes in SHADER_TYPES.items():
        if required_nodes <= node_names:
            return shader_type

    return None


def get_image_from_material(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Extracts the main albedo/diffuse texture from a material.

    Uses multiple detection strategies in order of reliability.
    Only returns textures connected to the material output.

    Args:
        mat: Material to extract image from.

    Returns:
        The albedo/diffuse image or None if no valid texture found.
    """
    if globs.is_blender_legacy:
        return get_image(get_texture(mat))

    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree

    # Try detection methods in order of reliability
    detection_methods = [
        lambda: _find_image_via_connection(mat),
        lambda: _find_image_from_specific_nodes(node_tree),
        lambda: _find_color_connected_image(node_tree),
        lambda: _find_image_from_shader_type(mat),
    ]

    for method in detection_methods:
        image = method()
        if image:
            return image

    return None


def get_diffuse(mat: bpy.types.Material) -> Tuple[int, int, int, int]:
    """Extracts the diffuse color from a material.

    Args:
        mat: Material to extract color from.

    Returns:
        RGBA color as integers (0-255) for atlas generation.
    """
    if not mat:
        return DEFAULT_DIFFUSE

    if globs.is_blender_legacy:
        return _rgb_to_srgb255(mat.diffuse_color)

    if not mat.node_tree or not mat.node_tree.nodes:
        return DEFAULT_DIFFUSE

    # Try connection-based detection
    output_node = _find_output_node(mat.node_tree.nodes)
    if output_node:
        shader_info = _trace_shader_from_output(output_node)
        if shader_info:
            shader_node, shader_type = shader_info
            color = _extract_shader_color(shader_node, shader_type)
            if color:
                return color

    # Try shader-specific accessors
    shader_type = get_shader_type(mat)
    if shader_type and shader_type in DIFFUSE_ACCESSORS:
        nodes = mat.node_tree.nodes
        try:
            accessor = DIFFUSE_ACCESSORS[shader_type]
            return _rgb_to_srgb255(accessor(nodes))
        except (KeyError, AttributeError, IndexError):
            pass

    return DEFAULT_DIFFUSE


def get_gfx_textures(
    mat: bpy.types.Material,
) -> Dict[str, bpy.types.PackedFile]:
    """Extracts graphics textures from a material's shader nodes.

    Searches for and extracts additional texture maps (metallic, roughness,
    specular, normal, emission) from Principled BSDF and Specular BSDF shaders.
    Only returns textures that are actually connected via image texture nodes.

    Supports:
        - Principled BSDF: All texture types including metallic
        - Specular BSDF: Roughness, specular, normal map, and emission

    Normal maps are detected through ShaderNodeNormalMap nodes connected
    to the shader's Normal input.

    Args:
        mat: Material to extract textures from.

    Returns:
        Dictionary mapping texture type names to packed file data.
        Empty dictionary if no compatible shader or textures found.
    """
    gfx_textures = {}
    if not mat.node_tree or not mat.node_tree.nodes:
        return gfx_textures

    shader_type = get_shader_type(mat)
    if not shader_type:
        return gfx_textures

    nodes = mat.node_tree.nodes

    shader_node = None
    input_mapping = None

    if "principled" in shader_type:
        shader_node = next(
            (
                node
                for node in nodes
                if node.bl_idname == "ShaderNodeBsdfPrincipled"
            ),
            None,
        )
        input_mapping = GFX_INPUT_NAMES

    elif "specular" in shader_type:
        shader_node = next(
            (
                node
                for node in nodes
                if node.bl_idname == "ShaderNodeEeveeSpecular"
            ),
            None,
        )
        input_mapping = SPECULAR_BSDF_INPUT_NAMES

    if not shader_node or not input_mapping:
        return gfx_textures

    for gfx_type, input_name in input_mapping.items():
        if not input_name:
            continue

        if input_name not in shader_node.inputs:
            continue

        socket = shader_node.inputs[input_name]
        image_node = _check_socket_for_image(socket)
        if image_node and image_node.image:
            packed_file = get_packed_file(image_node.image)
            if packed_file:
                gfx_textures[gfx_type] = packed_file

    return gfx_textures


def sort_materials(
    materials: List[bpy.types.Material],
) -> ValuesView[MatDictItem]:
    """Groups materials by texture and color for atlas generation.

    Args:
        materials: List of materials to process.

    Returns:
        Materials grouped by their texture/color combinations.
    """
    # Reset material references
    for mat in bpy.data.materials:
        mat.root_mat = None

    mat_dict = cast(MatDict, defaultdict(list))

    for mat in materials:
        if not mat:
            continue

        image = get_image_from_material(mat)
        packed_file = get_packed_file(image) if image else None
        diffuse = get_diffuse(mat)
        gfx_textures = get_gfx_textures(mat)
        gfx_textures_tuple = tuple(sorted(gfx_textures.items()))

        if packed_file:
            # Group by texture and optionally diffuse color
            key = (
                packed_file,
                diffuse if mat.smc_diffuse else DEFAULT_DIFFUSE,
                gfx_textures_tuple,
            )
        else:
            # Group by color only
            key = (diffuse, gfx_textures_tuple)

        mat_dict[key].append(mat)

    return mat_dict.values()


# Private helper functions


def _find_output_node(
    nodes: bpy.types.bpy_prop_collection,
) -> Optional[bpy.types.Node]:
    """Finds the material output node.

    Args:
        nodes: Node collection to search.

    Returns:
        Material output node or None.
    """
    # Try typed search first (most reliable)
    for node in nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial":
            return node

    # Fallback to name-based search
    for node in nodes:
        if "output" in node.name.lower():
            return node

    return None


def _trace_shader_from_output(
    node: bpy.types.Node,
) -> Optional[Tuple[bpy.types.Node, str]]:
    """Traces connections to find the main shader node.

    Args:
        node: Output node to trace from.

    Returns:
        Tuple of (shader_node, shader_type) or None.
    """
    if not node or not hasattr(node, "inputs"):
        return None

    for input_socket in node.inputs:
        if not input_socket.links:
            continue

        connected_node = input_socket.links[0].from_node
        node_type = connected_node.bl_idname

        if node_type not in SHADER_NODE_TYPES:
            # Not a shader, continue tracing
            return _trace_shader_from_output(connected_node)

        shader_type = SHADER_NODE_TYPES[node_type]

        # Handle node groups
        if isinstance(shader_type, dict):
            if (
                not hasattr(connected_node, "node_tree")
                or not connected_node.node_tree
            ):
                continue

            group_name = connected_node.node_tree.name
            if group_name in shader_type:
                return connected_node, shader_type[group_name]

            # Unknown group, continue tracing
            return _trace_shader_from_output(connected_node)

        return connected_node, shader_type

    return None


def _get_connected_nodes(
    start_node: bpy.types.Node, visited: Optional[Set[bpy.types.Node]] = None
) -> Set[bpy.types.Node]:
    """Recursively collects all nodes connected to the output.

    Args:
        start_node: Node to start traversal from.
        visited: Set of already visited nodes.

    Returns:
        Set of all connected nodes.
    """
    if visited is None:
        visited = set()

    if start_node in visited:
        return visited

    visited.add(start_node)

    if hasattr(start_node, "inputs"):
        for input_socket in start_node.inputs:
            for link in input_socket.links:
                _get_connected_nodes(link.from_node, visited)

    return visited


def _is_connected_to_output(
    node: bpy.types.Node, node_tree: bpy.types.NodeTree
) -> bool:
    """Checks if a node contributes to the final output.

    Args:
        node: Node to check.
        node_tree: Node tree containing the node.

    Returns:
        True if node is connected to output.
    """
    output_node = _find_output_node(node_tree.nodes)
    if not output_node:
        return False

    connected_nodes = _get_connected_nodes(output_node)
    return node in connected_nodes


def _is_image_texture_node(node: bpy.types.Node) -> bool:
    """Checks if a node is a valid image texture.

    Args:
        node: Node to check.

    Returns:
        True if node is an image texture with valid image.
    """
    return (
        node.bl_idname == "ShaderNodeTexImage"
        and hasattr(node, "image")
        and node.image is not None
    )


def _find_connected_image_node(
    shader_node: bpy.types.Node, shader_type: str = ""
) -> Optional[bpy.types.Node]:
    """Finds image texture connected to shader's color input.

    Only checks appropriate inputs for known shader types to avoid
    selecting wrong textures (metallic, normal, etc.).

    Args:
        shader_node: Shader node to search from.
        shader_type: Type of shader for input selection.

    Returns:
        Connected image texture node or None.
    """
    if not shader_node or not hasattr(shader_node, "inputs"):
        return None

    # Determine the appropriate input name
    priority_input = None

    if shader_node.bl_idname == "ShaderNodeBsdfPrincipled":
        priority_input = "Base Color"
    elif shader_node.bl_idname == "ShaderNodeBsdfDiffuse":
        priority_input = "Color"
    elif shader_node.bl_idname == "ShaderNodeEeveeSpecular":
        priority_input = "Base Color"
    elif shader_node.bl_idname == "ShaderNodeEmission":
        priority_input = "Color"
    elif shader_type in SHADER_ALBEDO_INPUTS:
        priority_input = SHADER_ALBEDO_INPUTS[shader_type]

    # Check priority input first
    if priority_input and priority_input in shader_node.inputs:
        result = _check_socket_for_image(shader_node.inputs[priority_input])
        if result:
            return result

    # Check common color inputs as fallback
    for input_name in COLOR_INPUT_NAMES:
        if input_name in shader_node.inputs:
            result = _check_socket_for_image(shader_node.inputs[input_name])
            if result:
                return result

    return None


def _check_socket_for_image(
    socket: bpy.types.NodeSocket,
) -> Optional[bpy.types.Node]:
    """Checks if a socket has an image texture connected.

    Args:
        socket: Node socket to check.

    Returns:
        Connected image texture node or None.
    """
    if not socket.links:
        return None

    for link in socket.links:
        from_node = link.from_node

        if _is_image_texture_node(from_node):
            return from_node

        # Check indirect connections
        image_node = _find_image_in_tree(from_node)
        if image_node:
            return image_node

    return None


def _find_image_in_tree(
    node: bpy.types.Node, visited: Optional[Set[bpy.types.Node]] = None
) -> Optional[bpy.types.Node]:
    """Recursively searches for image textures in node tree.

    Args:
        node: Starting node.
        visited: Set of visited nodes.

    Returns:
        Image texture node or None.
    """
    if visited is None:
        visited = set()

    if node in visited:
        return None
    visited.add(node)

    if _is_image_texture_node(node):
        return node

    # Search inputs first (typical for mix nodes)
    if hasattr(node, "inputs"):
        for socket in node.inputs:
            for link in socket.links:
                result = _find_image_in_tree(link.from_node, visited)
                if result:
                    return result

    return None


def _find_image_via_connection(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Finds image through output connection tracing.

    Args:
        mat: Material to analyze.

    Returns:
        Found image or None.
    """
    if not mat.node_tree:
        return None

    output_node = _find_output_node(mat.node_tree.nodes)
    if not output_node:
        return None

    shader_info = _trace_shader_from_output(output_node)
    if not shader_info:
        return None

    shader_node, shader_type = shader_info
    image_node = _find_connected_image_node(shader_node, shader_type)

    return image_node.image if image_node else None


def _find_image_from_specific_nodes(
    node_tree: bpy.types.NodeTree,
) -> Optional[bpy.types.Image]:
    """Finds image from known shader-specific nodes.

    Args:
        node_tree: Node tree to search.

    Returns:
        Found image or None.
    """
    nodes = node_tree.nodes

    # Check MMD texture
    if MMD_TEXTURE_NODE in nodes:
        node = nodes[MMD_TEXTURE_NODE]
        if hasattr(node, "image") and _is_connected_to_output(node, node_tree):
            return node.image

    # Check MToon texture
    if MTOON_TEXTURE_NODE in nodes:
        node = nodes[MTOON_TEXTURE_NODE]
        if hasattr(node, "image") and _is_connected_to_output(node, node_tree):
            return node.image

    return None


def _find_color_connected_image(
    node_tree: bpy.types.NodeTree,
) -> Optional[bpy.types.Image]:
    """Finds images connected to color inputs of shaders.

    Args:
        node_tree: Node tree to search.

    Returns:
        Image connected to a color input or None.
    """
    output_node = _find_output_node(node_tree.nodes)
    if not output_node:
        return None

    connected_nodes = _get_connected_nodes(output_node)

    # Find shaders connected to output
    for node in connected_nodes:
        if node.bl_idname not in SHADER_NODE_TYPES:
            continue

        if not hasattr(node, "inputs"):
            continue

        # Check color inputs
        for socket in node.inputs:
            if any(
                term in socket.name.lower()
                for term in ["color", "diffuse", "base"]
            ):
                if not socket.links:
                    continue

                for link in socket.links:
                    from_node = link.from_node
                    if _is_image_texture_node(from_node):
                        return from_node.image

                    # Check indirect connections
                    image_node = _find_image_in_tree(from_node)
                    if image_node:
                        if hasattr(image_node, "image"):
                            return image_node.image

    return None


def _find_image_from_shader_type(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Finds image based on detected shader type.

    Args:
        mat: Material to analyze.

    Returns:
        Found image or None.
    """
    shader_type = get_shader_type(mat)
    if not shader_type or shader_type not in SHADER_IMAGE_NODES:
        return None

    node_name = SHADER_IMAGE_NODES[shader_type]
    node_tree = mat.node_tree

    if node_name not in node_tree.nodes:
        return None

    node = node_tree.nodes[node_name]
    if hasattr(node, "image") and _is_connected_to_output(node, node_tree):
        return node.image

    return None


def _detect_group_shader(nodes: bpy.types.bpy_prop_collection) -> Optional[str]:
    """Detects specialized group-based shaders.

    Args:
        nodes: Node collection to check.

    Returns:
        Shader type identifier or None.
    """
    if "Group" not in nodes:
        return None

    group_node = nodes["Group"]
    if not hasattr(group_node, "node_tree") or not group_node.node_tree:
        return None

    tree_name = group_node.node_tree.name

    if tree_name == "Group":
        return "xnalaraNewCol"
    elif tree_name == "MToon_unversioned":
        return "vrm" if "Image Texture" in nodes else "vrmCol"
    elif tree_name == "XPS Shader" and "Image Texture" in nodes:
        return "xnalara"

    return None


def _extract_shader_color(
    shader_node: bpy.types.Node, shader_type: str
) -> Optional[Tuple[int, int, int, int]]:
    """Extracts color from a shader node.

    Args:
        shader_node: Shader node.
        shader_type: Type of shader.

    Returns:
        RGBA color values (0-255) or None.
    """
    input_map = {
        "principled": "Base Color",
        "diffuse": "Color",
        "specular": "Base Color",
        "emission": "Color",
    }

    input_name = input_map.get(shader_type)
    if input_name and input_name in shader_node.inputs:
        return _rgb_to_srgb255(shader_node.inputs[input_name].default_value)

    return None


def _rgb_to_srgb255(color: Diffuse) -> Tuple[int, int, int, int]:
    """Converts linear RGB to sRGB (0-255) with gamma correction.

    Args:
        color: Linear RGB values (0-1).

    Returns:
        sRGB values (0-255).
    """
    result = []

    for c in color:
        if c <= 0.0:
            srgb = 0.0
        elif c < GAMMA_THRESHOLD:
            srgb = c * LINEAR_FACTOR
        else:
            srgb = GAMMA_FACTOR * pow(c, 1.0 / GAMMA) - GAMMA_OFFSET

        result.append(int(np.clip(round(srgb * 255), 0, 255)))

    return tuple(result)
