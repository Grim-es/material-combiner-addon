"""Utilities for handling and processing Blender materials.

This module provides functions for detecting material types, extracting textures,
and preparing materials for atlas generation in the Material Combiner addon.
It handles different shader types and Blender versions with support for MMD,
MToon, Principled BSDF, and other material systems.
"""

from collections import OrderedDict, defaultdict
from typing import List, Optional, Set, Tuple, ValuesView, cast

import bpy
import numpy as np

from .. import globs
from ..type_annotations import Diffuse, MatDict, MatDictItem
from .images import get_image, get_packed_file
from .textures import get_texture

# Gamma correction constants for proper sRGB to linear conversion
GAMMA_THRESHOLD = 0.0031308
LINEAR_FACTOR = 12.92
GAMMA_FACTOR = 1.055
DEFAULT_DIFFUSE = (255, 255, 255, 255)

# Node types that correspond to specific shader types for material detection
SHADER_NODE_TYPES = {
    "ShaderNodeBsdfPrincipled": "principled",
    "ShaderNodeBsdfDiffuse": "diffuse",
    "ShaderNodeEmission": "emission",
    "ShaderNodeGroup": {
        "MToon_unversioned": "vrm",
        "XPS Shader": "xnalara",
        "Group": "xnalaraNew",
    },
}

# Known shader names and textures for MMD and MToon material detection
MMD_SHADER_NAMES = {"mmd_shader"}
MMD_TEXTURE_NAMES = {"mmd_base_tex"}
MTOON_SHADER_NAMES = {"Mtoon1Material.Mtoon1Output"}
MTOON_TEXTURE_NAMES = {"Mtoon1BaseColorTexture.Image"}

# Map of shader types to node names for classification
SHADER_TYPES = OrderedDict(
    [
        ("mmd", {"mmd_shader", "mmd_base_tex"}),
        ("mmdCol", {"mmd_shader"}),
        ("mtoon", {"Mtoon1BaseColorTexture.Image"}),
        ("mtoonCol", {"Mtoon1Material.Mtoon1Output"}),
        ("principled", {"Principled BSDF", "Image Texture"}),
        ("principledCol", {"Principled BSDF"}),
        ("diffuse", {"Diffuse BSDF", "Image Texture"}),
        ("diffuseCol", {"Diffuse BSDF"}),
        ("emission", {"Emission", "Image Texture"}),
        ("emissionCol", {"Emission"}),
    ]
)

# Map of shader types to their corresponding albedo texture node names for extraction
SHADER_IMAGE_NODES = {
    "mmd": "mmd_base_tex",
    "mtoon": "Mtoon1BaseColorTexture.Image",
    "vrm": "Image Texture",
    "xnalara": "Image Texture",
    "principled": "Image Texture",
    "diffuse": "Image Texture",
    "emission": "Image Texture",
}

# Map of shader types to the input names that typically connect to albedo textures
SHADER_ALBEDO_INPUTS = {
    "principled": "Base Color",
    "diffuse": "Color",
    "emission": "Color",
    "mmd": "Diffuse Color",
    "mtoon": "Base Color",
    "vrm": "Color",
    "xnalara": "Diffuse",
    "xnalaraNew": "Diffuse",
}

# Common color-related input names across different shaders
COLOR_INPUT_NAMES = ["Color", "Base Color", "Diffuse Color", "BaseColor"]

# Diffuse color accessors by shader type for reliable color extraction
DIFFUSE_ACCESSORS = {
    "mmdCol": lambda nodes: nodes["mmd_shader"]
    .inputs["Diffuse Color"]
    .default_value,
    "mtoonCol": lambda nodes: nodes[
        "Mtoon1PbrMetallicRoughness.BaseColorFactor"
    ].color,
    "vrm": lambda nodes: nodes["RGB"].outputs[0].default_value,
    "vrmCol": lambda nodes: nodes["Group"].inputs[10].default_value,
    "diffuseCol": lambda nodes: nodes["Diffuse BSDF"]
    .inputs["Color"]
    .default_value,
    "xnalaraNewCol": lambda nodes: nodes["Group"]
    .inputs["Diffuse"]
    .default_value,
    "principledCol": lambda nodes: nodes["Principled BSDF"]
    .inputs["Base Color"]
    .default_value,
    "xnalaraCol": lambda nodes: nodes["Principled BSDF"]
    .inputs["Base Color"]
    .default_value,
}


def get_materials(ob: bpy.types.Object) -> List[bpy.types.Material]:
    """Retrieves all materials assigned to a Blender object.

    Args:
        ob: Blender object from which to extract materials.

    Returns:
        List of materials assigned to the object, excluding empty slots.
    """
    return [
        mat_slot.material for mat_slot in ob.material_slots if mat_slot.material
    ]


def get_shader_type(mat: bpy.types.Material) -> Optional[str]:
    """Identifies the shader type of a material through node analysis.

    Uses multiple detection methods to determine the shader type:
    1. Connection-based detection (following from output node).
    2. Group node detection for special cases (XNALara, VRM, etc.).
    3. Specific shader name detection (MMD, MToon).
    4. Node name pattern matching.

    Args:
        mat: Material to analyze.

    Returns:
        String identifier of a shader type or None if not recognized.
        Types with "Col" suffix indicate materials using only colors without textures.
    """
    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree.nodes
    shader_type = None

    # 1. First try connection-based detection (most robust)
    output_node = _find_output_node(node_tree)
    if output_node:
        shader_result = _trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result

            # Check if this shader has an image texture connected
            image_node = _find_connected_image_node(shader_node, shader_type)
            if image_node:
                return shader_type
            else:
                # No texture, use color variant
                return "{}Col".format(shader_type)

    # 2. Fallback to group node detection (special cases)
    if not shader_type:
        shader_type = _detect_group_shader(node_tree)

    # 3. Check for specific shader types by name sets
    if not shader_type:
        node_names_set = set(node_tree.keys())
        if MMD_SHADER_NAMES.intersection(node_names_set):
            shader_type = (
                "mmd"
                if MMD_TEXTURE_NAMES.intersection(node_names_set)
                else "mmdCol"
            )
        elif MTOON_SHADER_NAMES.intersection(node_names_set):
            shader_type = (
                "mtoon"
                if MTOON_TEXTURE_NAMES.intersection(node_names_set)
                else "mtoonCol"
            )
        else:
            # 4. As last resort, check against predefined shader types
            for shader, node_names in SHADER_TYPES.items():
                if node_names.issubset(node_names_set):
                    shader_type = shader
                    break

    return shader_type


def _find_image_from_connection_detection(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Finds image through connection-based detection.

    Args:
        mat: Material to analyze.

    Returns:
        Found image or None if no image is detected.
    """
    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree

    # Connection-based detection (most reliable)
    output_node = _find_output_node(node_tree.nodes)
    if output_node:
        shader_result = _trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result
            image_node = _find_connected_image_node(shader_node, shader_type)
            if image_node and hasattr(image_node, "image"):
                return image_node.image

    return None


def _find_image_from_specific_nodes(
    node_tree: bpy.types.NodeTree,
) -> Optional[bpy.types.Image]:
    """Finds image from specific known nodes like MMD and MToon.

    Args:
        node_tree: Node tree to search in.

    Returns:
        Found image or None if no image is found in specified nodes.
    """
    # MMD-specific detection
    if "mmd_base_tex" in node_tree.nodes and hasattr(
        node_tree.nodes["mmd_base_tex"], "image"
    ):
        return node_tree.nodes["mmd_base_tex"].image

    # MToon-specific detection
    if "Mtoon1BaseColorTexture.Image" in node_tree.nodes and hasattr(
        node_tree.nodes["Mtoon1BaseColorTexture.Image"], "image"
    ):
        return node_tree.nodes["Mtoon1BaseColorTexture.Image"].image

    return None


def _find_image_from_any_texture_node(
    node_tree: bpy.types.NodeTree,
) -> Optional[bpy.types.Image]:
    """Finds any image texture node in the material.

    Args:
        node_tree: Node tree to search in.

    Returns:
        First found image from any texture node or None if no image texture nodes exist.
    """
    for node in node_tree.nodes:
        if _is_image_texture_node(node):
            return node.image
    return None


def _find_image_from_shader_type(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Finds image based on material's detected shader type.

    Args:
        mat: Material to analyze.

    Returns:
        Found image or None if no image is found or shader type is not recognized.
    """
    shader = get_shader_type(mat)
    if not shader or shader not in SHADER_IMAGE_NODES:
        return None

    node_name = SHADER_IMAGE_NODES[shader]
    node_tree = mat.node_tree

    if node_name in node_tree.nodes:
        node = node_tree.nodes[node_name]
        if hasattr(node, "image"):
            return node.image

    return None


def get_image_from_material(
    mat: bpy.types.Material,
) -> Optional[bpy.types.Image]:
    """Extracts the main albedo/diffuse image from a material.

    Uses multiple detection methods in order of reliability to find the appropriate
    texture for atlas generation.

    Args:
        mat: Material to extract image from.

    Returns:
        The albedo/diffuse image or None if no texture is found.
    """
    if globs.is_blender_legacy:
        return get_image(get_texture(mat))

    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree
    result_image = None

    # Try different detection methods in order of reliability
    detection_methods = [
        lambda: _find_image_from_connection_detection(mat),
        lambda: _find_image_from_specific_nodes(node_tree),
        lambda: _find_color_connected_image(node_tree),
        lambda: _find_image_from_any_texture_node(node_tree),
        lambda: _find_image_from_shader_type(mat),
    ]

    for method in detection_methods:
        result_image = method()
        if result_image:
            break

    return result_image


def get_diffuse(mat: bpy.types.Material) -> Tuple[int, int, int, int]:
    """Extracts the diffuse color from a material for atlas generation.

    Handles different shader types and Blender versions to get the base color
    for each material. Used to determine how non-textured areas or color-only
    materials are handled in the atlas.

    Args:
        mat: Material to extract diffuse color from.

    Returns:
        RGBA color values as a tuple of integers (0-255), ready for use with Pillow.
    """
    # Default diffuse color as fallback
    diffuse_color = DEFAULT_DIFFUSE

    if not mat:
        return diffuse_color

    if globs.is_blender_legacy:
        return _rgb_to_255_scale(mat.diffuse_color)

    # For Blender 2.80+, use node-based detection
    if not mat.node_tree or not mat.node_tree.nodes:
        return diffuse_color

    # 1. Try connection-based detection first
    output_node = _find_output_node(mat.node_tree.nodes)
    if output_node:
        shader_result = _trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result
            color = _get_color_from_shader_node(shader_node, shader_type)
            if color:
                diffuse_color = color

    # If connection-based detection didn't work, try shader-specific detection
    if diffuse_color == DEFAULT_DIFFUSE:
        shader = get_shader_type(mat)

        if shader:
            node_tree = mat.node_tree.nodes

            # Use the accessor function for this shader type if available
            accessor = DIFFUSE_ACCESSORS.get(shader)
            if accessor and all(
                required_node in node_tree
                for required_node in _get_required_nodes(shader)
            ):
                try:
                    diffuse_color = _rgb_to_255_scale(accessor(node_tree))
                except (KeyError, AttributeError):
                    # If access fails, keep the default diffuse color
                    pass

    return diffuse_color


def sort_materials(
    mat_list: List[bpy.types.Material],
) -> ValuesView[MatDictItem]:
    """Groups materials by their textures and diffuse colors for combining.

    Determines which materials can be combined into the same atlas based on
    identical textures and similar colors.

    Args:
        mat_list: List of materials to group.

    Returns:
        Materials grouped by texture/color combinations for atlas creation.
    """
    # Reset material references
    for mat in bpy.data.materials:
        mat.root_mat = None

    mat_dict = cast(MatDict, defaultdict(list))
    for mat in mat_list:
        if not mat:
            continue

        packed_file = None

        image = get_image_from_material(mat)
        if image:
            packed_file = get_packed_file(image)

        # Get diffuse color (always RGBA)
        diffuse_rgba = get_diffuse(mat)

        if packed_file:
            key = (
                packed_file,
                diffuse_rgba if mat.smc_diffuse else DEFAULT_DIFFUSE,
            )
            mat_dict[key].append(mat)
        else:
            mat_dict[diffuse_rgba].append(mat)

    return mat_dict.values()


def _find_nodes_by_type(
    nodes: bpy.types.bpy_prop_collection, node_type: str
) -> List[bpy.types.Node]:
    """Locates all nodes of a specific type in a node tree.

    Args:
        nodes: Node tree to search in.
        node_type: Blender node type identifier.

    Returns:
        List of nodes matching the specified type.
    """
    return [node for node in nodes if node.bl_idname == node_type]


def _find_output_node(
    nodes: bpy.types.bpy_prop_collection,
) -> Optional[bpy.types.Node]:
    """Locates the output node in a material node tree.

    The output node is the starting point for tracing node connections
    in the material graph.

    Args:
        nodes: Node tree to search in.

    Returns:
        The output node or None if not found.
    """
    # Try to find by type first (most reliable)
    output_nodes = _find_nodes_by_type(nodes, "ShaderNodeOutputMaterial")
    if output_nodes:
        return output_nodes[0]

    # Fallback to finding by name
    for node in nodes:
        if "Output" in node.name or "output" in node.name.lower():
            return node

    return None


def _trace_connected_shader(
    node: bpy.types.Node,
) -> Optional[Tuple[bpy.types.Node, str]]:
    """Traces node connections from output to find the connected shader.

    Follows links backward from the output node to identify the primary
    shader responsible for the material's appearance.

    Args:
        node: Output node to trace connections from.

    Returns:
        Tuple of (shader_node, shader_type) or None if no shader is connected.
    """
    if not node or not node.inputs:
        return None

    # Get the first connected node (usually "Surface" input for output nodes)
    for input_socket in node.inputs:
        if input_socket.links:
            connected_node = input_socket.links[0].from_node

            # Check if this is a shader node by type
            node_type = connected_node.bl_idname
            if node_type in SHADER_NODE_TYPES:
                shader_type = SHADER_NODE_TYPES[node_type]

                # Handle node groups with different internal node trees
                if node_type == "ShaderNodeGroup" and connected_node.node_tree:
                    group_name = connected_node.node_tree.name

                    if group_name in shader_type:
                        shader_type = shader_type[group_name]
                    else:
                        return _trace_connected_shader(connected_node)

                return connected_node, shader_type

            # Not a shader, continue recursively
            return _trace_connected_shader(connected_node)

    return None


def _is_image_texture_node(node: bpy.types.Node) -> bool:
    """Determines whether a node is an image texture with a valid image.

    Args:
        node: Node to check.

    Returns:
        True if node is an image texture with a valid image, False otherwise.
    """
    return (
        node.bl_idname == "ShaderNodeTexImage"
        and hasattr(node, "image")
        and node.image is not None
    )


def _find_image_texture_in_node_tree(
    node: bpy.types.Node, visited: Optional[Set[bpy.types.Node]] = None
) -> Optional[bpy.types.Node]:
    """Recursively searches for an image texture node in the material graph.

    Traverses complex shader graphs to find texture nodes that might be connected
    through intermediary nodes like mixers or converters.

    Args:
        node: Starting node for recursive search.
        visited: Set of visited nodes to prevent infinite loops.

    Returns:
        Image texture node or None if not found.
    """
    if visited is None:
        visited = set()

    # Avoid infinite recursion by tracking visited nodes
    if node in visited:
        return None
    visited.add(node)

    # Check if this is an image texture node
    if _is_image_texture_node(node):
        return node

    # Check all inputs of this node first (for mixing nodes that typically connect images to inputs)
    if hasattr(node, "inputs"):
        for input_socket in node.inputs:
            if input_socket.links:
                for link in input_socket.links:
                    result = _find_image_texture_in_node_tree(
                        link.from_node, visited
                    )
                    if result:
                        return result

    # Then check all outputs of this node
    if hasattr(node, "outputs"):
        for output in node.outputs:
            for link in output.links:
                result = _find_image_texture_in_node_tree(link.to_node, visited)
                if result:
                    return result

    return None


def _check_input_for_image(
    input_socket: bpy.types.NodeSocket,
) -> Optional[bpy.types.Node]:
    """Checks a specific input socket for connected image textures.

    Args:
        input_socket: Input socket to check for image connections.

    Returns:
        Connected image texture node or None if no image is connected.
    """
    if not input_socket.links:
        return None

    for link in input_socket.links:
        from_node = link.from_node

        # Direct image texture connection
        if _is_image_texture_node(from_node):
            return from_node

        # Check for indirect connections
        image_node = _find_image_texture_in_node_tree(from_node, set())
        if image_node:
            return image_node

    return None


def _get_priority_input_name(
    shader_node: bpy.types.Node, shader_type: str
) -> Optional[str]:
    """Determines the priority input name based on shader node and type.

    Args:
        shader_node: The shader node to analyze.
        shader_type: Type of shader.

    Returns:
        The name of the priority input or None if no priority input is identified.
    """
    # First check based on a node type
    if shader_node.bl_idname == "ShaderNodeBsdfPrincipled":
        return "Base Color"
    elif shader_node.bl_idname == "ShaderNodeBsdfDiffuse":
        return "Color"
    elif shader_node.bl_idname == "ShaderNodeEmission":
        return "Color"

    # Fallback to shader type mapping
    if shader_type and shader_type in SHADER_ALBEDO_INPUTS:
        return SHADER_ALBEDO_INPUTS[shader_type]

    return None


def _find_connected_image_node(
    shader_node: bpy.types.Node, shader_type: str = ""
) -> Optional[bpy.types.Node]:
    """Locates an image texture connected to a shader's albedo/color input.

    Prioritizes connections to inputs typically used for base color or albedo textures,
    which are the primary targets for atlas generation.

    Args:
        shader_node: Shader node to search from.
        shader_type: Type of shader for prioritizing specific inputs.

    Returns:
        Connected image texture node or None if not found.
    """
    if (
        not shader_node
        or not hasattr(shader_node, "inputs")
        or not shader_node.inputs
    ):
        return None

    # 1. Check priority input based on a shader type
    priority_input = _get_priority_input_name(shader_node, shader_type)

    # 2. Try priority input first if available
    if priority_input and priority_input in shader_node.inputs:
        result = _check_input_for_image(shader_node.inputs[priority_input])
        if result:
            return result

    # 3. Try standard color inputs
    for input_name in COLOR_INPUT_NAMES:
        if input_name in shader_node.inputs:
            result = _check_input_for_image(shader_node.inputs[input_name])
            if result:
                return result

    # 4. Try all other inputs as last resort
    for input_socket in shader_node.inputs:
        if input_socket.name not in COLOR_INPUT_NAMES:
            result = _check_input_for_image(input_socket)
            if result:
                return result

    return None


def _find_shader_nodes(node_tree: bpy.types.NodeTree) -> List[bpy.types.Node]:
    """Identifies all shader nodes in a material node tree.

    Args:
        node_tree: Node tree to search in.

    Returns:
        List of shader nodes found in the material.
    """
    shader_nodes = []
    for node in node_tree.nodes:
        if node.bl_idname in SHADER_NODE_TYPES or (
            node.bl_idname == "ShaderNodeGroup"
            and hasattr(node, "node_tree")
            and node.node_tree
            and node.node_tree.name
            in SHADER_NODE_TYPES.get("ShaderNodeGroup", {})
        ):
            shader_nodes.append(node)
    return shader_nodes


def _find_color_connected_image(
    node_tree: bpy.types.NodeTree,
) -> Optional[bpy.types.Image]:
    """Finds an image connected to any color-related input in the material.

    Provides a fallback way to locate albedo/base textures when the standard
    connection patterns aren't found.

    Args:
        node_tree: Node tree to search in.

    Returns:
        Image connected to a color input or None if not found.
    """
    shader_nodes = _find_shader_nodes(node_tree)

    for shader_node in shader_nodes:
        for input_socket in shader_node.inputs:
            if any(
                color_term in input_socket.name.lower()
                for color_term in ["color", "diffuse", "base"]
            ):
                if input_socket.links:
                    for link in input_socket.links:
                        from_node = link.from_node
                        if _is_image_texture_node(from_node):
                            return from_node.image

                        # Try recursive search
                        image_node = _find_image_texture_in_node_tree(
                            from_node, set()
                        )
                        if image_node and hasattr(image_node, "image"):
                            return image_node.image
    return None


def _detect_group_shader(nodes: bpy.types.bpy_prop_collection) -> Optional[str]:
    """Identifies specialized group-based shaders used in imported models.

    Args:
        nodes: Node tree to check.

    Returns:
        Shader type identifier or None if not recognized.
    """
    if "Group" not in nodes or not hasattr(nodes["Group"], "node_tree"):
        return None

    node_tree_name = (
        nodes["Group"].node_tree.name if nodes["Group"].node_tree else ""
    )

    if node_tree_name == "Group":
        return "xnalaraNewCol"
    if node_tree_name == "MToon_unversioned":
        return "vrm" if "Image Texture" in nodes else "vrmCol"
    elif node_tree_name == "XPS Shader" and "Image Texture" in nodes:
        return "xnalara"

    return None


def _get_required_nodes(shader_type: str) -> Set[str]:
    """Determines the essential nodes needed for a specific shader type.

    Args:
        shader_type: Shader type to get required nodes for.

    Returns:
        Set of node names required for the shader type.
    """
    if shader_type in SHADER_TYPES:
        return SHADER_TYPES[shader_type]

    # Special cases for derived shader types
    if shader_type == "xnalaraCol":
        return {"Principled BSDF"}

    return set()


def _get_color_from_shader_node(
    shader_node: bpy.types.Node, shader_type: str
) -> Optional[Tuple[int, int, int, int]]:
    """Extracts the base color directly from a shader node.

    Args:
        shader_node: Shader node to extract color from.
        shader_type: Type of shader.

    Returns:
        RGBA color values or None if color input not found.
    """
    if shader_type == "principled" and "Base Color" in shader_node.inputs:
        return _rgb_to_255_scale(shader_node.inputs["Base Color"].default_value)
    elif shader_type == "diffuse" and "Color" in shader_node.inputs:
        return _rgb_to_255_scale(shader_node.inputs["Color"].default_value)
    elif shader_type == "emission" and "Color" in shader_node.inputs:
        return _rgb_to_255_scale(shader_node.inputs["Color"].default_value)
    return None


def _rgb_to_255_scale(diffuse: Diffuse) -> Diffuse:
    """Converts RGB float values to 8-bit integer values with gamma correction.

    Transforms Blender's linear color values (0-1) to sRGB values (0-255)
    suitable for processing with Pillow during atlas generation.

    Args:
        diffuse: RGB or RGBA color values in 0-1 range.

    Returns:
        Color values converted to 0-255 range with gamma correction.
    """
    rgb = np.empty(shape=(0,), dtype=int)
    for c in diffuse:
        if c < 0.0:
            srgb = 0
        elif c < GAMMA_THRESHOLD:
            srgb = c * LINEAR_FACTOR
        else:
            srgb = GAMMA_FACTOR * pow(c, 1.0 / 2.4) - 0.055
        rgb = np.append(rgb, np.clip(round(srgb * 255), 0, 255))
    return tuple(rgb)
