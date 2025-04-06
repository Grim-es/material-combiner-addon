from collections import OrderedDict, defaultdict
from typing import List, Optional, Tuple, Union, ValuesView, cast

import bpy
import numpy as np

from .. import globs
from ..type_annotations import Diffuse, MatDict, MatDictItem
from .images import get_image, get_packed_file
from .textures import get_texture

# Node types that correspond to specific shader types
SHADER_NODE_TYPES = {
    'ShaderNodeBsdfPrincipled': 'principled',
    'ShaderNodeBsdfDiffuse': 'diffuse',
    'ShaderNodeEmission': 'emission',
    'ShaderNodeGroup': {
        'MToon_unversioned': 'vrm',
        'XPS Shader': 'xnalara',
        'Group': 'xnalaraNew',
    }
}

# Known shader names and textures for different material types
MMD_SHADER_NAMES = {'mmd_shader'}
MMD_TEXTURE_NAMES = {'mmd_base_tex'}
MTOON_SHADER_NAMES = {'Mtoon1Material.Mtoon1Output'}
MTOON_TEXTURE_NAMES = {'Mtoon1BaseColorTexture.Image'}

# Map of shader types to node names
shader_types = OrderedDict([
    ('mmd', {'mmd_shader', 'mmd_base_tex'}),
    ('mmdCol', {'mmd_shader'}),
    ('mtoon', {'Mtoon1BaseColorTexture.Image'}),
    ('mtoonCol', {'Mtoon1Material.Mtoon1Output'}),
    ('principled', {'Principled BSDF', 'Image Texture'}),
    ('principledCol', {'Principled BSDF'}),
    ('diffuse', {'Diffuse BSDF', 'Image Texture'}),
    ('diffuseCol', {'Diffuse BSDF'}),
    ('emission', {'Emission', 'Image Texture'}),
    ('emissionCol', {'Emission'}),
])

# Map of shader types to their corresponding albedo texture node names
shader_image_nodes = {
    'mmd': 'mmd_base_tex',
    'mtoon': 'Mtoon1BaseColorTexture.Image',
    'vrm': 'Image Texture',
    'xnalara': 'Image Texture',
    'principled': 'Image Texture',
    'diffuse': 'Image Texture',
    'emission': 'Image Texture',
}

# Map of shader types to the input names that typically connect to albedo textures
shader_albedo_inputs = {
    'principled': 'Base Color',
    'diffuse': 'Color',
    'emission': 'Color',
    'mmd': 'Diffuse Color',
    'mtoon': 'Base Color',
    'vrm': 'Color',
    'xnalara': 'Diffuse',
    'xnalaraNew': 'Diffuse'
}

# Common color-related input names across different shaders
COLOR_INPUT_NAMES = ['Color', 'Base Color', 'Diffuse Color', 'BaseColor']


def get_materials(ob: bpy.types.Object) -> List[bpy.types.Material]:
    """Get all materials from an object."""
    return [mat_slot.material for mat_slot in ob.material_slots if mat_slot.material]


def find_nodes_by_type(nodes, node_type: str) -> List[bpy.types.Node]:
    """Find all nodes of a specific type in a node tree."""
    return [node for node in nodes if node.bl_idname == node_type]


def find_output_node(nodes) -> Optional[bpy.types.Node]:
    """Find the output node in a material node tree."""
    # Try to find by type first (most reliable)
    output_nodes = find_nodes_by_type(nodes, 'ShaderNodeOutputMaterial')
    if output_nodes:
        return output_nodes[0]

    # Fallback to finding by name
    for node in nodes:
        if 'Output' in node.name or 'output' in node.name.lower():
            return node

    return None


def trace_connected_shader(node: bpy.types.Node) -> Optional[Tuple[bpy.types.Node, str]]:
    """
    Trace from output node to find the connected shader node.
    Returns the shader node and its detected type.
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
                if node_type == 'ShaderNodeGroup' and connected_node.node_tree:
                    group_name = connected_node.node_tree.name
                    if group_name in SHADER_NODE_TYPES['ShaderNodeGroup']:
                        shader_type = SHADER_NODE_TYPES['ShaderNodeGroup'][group_name]

                return connected_node, shader_type

            # Not a shader, continue recursively
            return trace_connected_shader(connected_node)

    return None


def is_image_texture_node(node: bpy.types.Node) -> bool:
    """Check if a node is an image texture node with a valid image."""
    return (node.bl_idname == 'ShaderNodeTexImage' and 
            hasattr(node, 'image') and 
            node.image is not None)


def find_image_texture_in_node_tree(node: bpy.types.Node, visited=None) -> Optional[bpy.types.Node]:
    """Recursively find an image texture node in the node tree."""
    if visited is None:
        visited = set()
        
    # Avoid infinite recursion by tracking visited nodes
    if node in visited:
        return None
    visited.add(node)
    
    # Check if this is an image texture node
    if is_image_texture_node(node):
        return node

    # Check all inputs of this node first (for mixing nodes that typically connect images to inputs)
    if hasattr(node, 'inputs'):
        for input_socket in node.inputs:
            if input_socket.links:
                for link in input_socket.links:
                    result = find_image_texture_in_node_tree(link.from_node, visited)
                    if result:
                        return result
    
    # Then check all outputs of this node
    for output in node.outputs:
        for link in output.links:
            result = find_image_texture_in_node_tree(link.to_node, visited)
            if result:
                return result

    return None


def find_connected_image_node(shader_node: bpy.types.Node, shader_type: str = None) -> Optional[bpy.types.Node]:
    """
    Find image texture node connected to a shader node by tracing inputs.
    Prioritizes the shader's albedo/color input based on shader type.
    """
    if not shader_node or not shader_node.inputs:
        return None
    
    # Get the appropriate albedo input name based on shader type
    priority_input = None
    if shader_type and shader_type in shader_albedo_inputs:
        priority_input = shader_albedo_inputs[shader_type]
    
    # Override with explicit shader type checks based on node type
    if shader_node.bl_idname == 'ShaderNodeBsdfPrincipled':
        priority_input = 'Base Color'
    elif shader_node.bl_idname == 'ShaderNodeBsdfDiffuse':
        priority_input = 'Color'
    elif shader_node.bl_idname == 'ShaderNodeEmission':
        priority_input = 'Color'
    
    # First try the priority input if available
    if priority_input and priority_input in shader_node.inputs and shader_node.inputs[priority_input].links:
        input_socket = shader_node.inputs[priority_input]
        for link in input_socket.links:
            from_node = link.from_node
            
            # Direct image texture connection
            if is_image_texture_node(from_node):
                return from_node
                
            # Check for other nodes that might lead to an image texture
            image_node = find_image_texture_in_node_tree(from_node, set())
            if image_node:
                return image_node
    
    # Fallback to checking standard color inputs
    for input_name in COLOR_INPUT_NAMES:
        if input_name in shader_node.inputs and shader_node.inputs[input_name].links:
            input_socket = shader_node.inputs[input_name]
            for link in input_socket.links:
                from_node = link.from_node
                
                # Direct image texture connection
                if is_image_texture_node(from_node):
                    return from_node
                    
                # Check for other nodes that might lead to an image texture
                image_node = find_image_texture_in_node_tree(from_node, set())
                if image_node:
                    return image_node
    
    # Last resort: check all other inputs
    for input_socket in shader_node.inputs:
        if not input_socket.links or input_socket.name in COLOR_INPUT_NAMES:
            continue

        for link in input_socket.links:
            from_node = link.from_node

            # Direct image texture connection
            if is_image_texture_node(from_node):
                return from_node

            # Check for other nodes that might lead to an image texture
            image_node = find_image_texture_in_node_tree(from_node, set())
            if image_node:
                return image_node

    return None


def get_shader_type(mat: bpy.types.Material) -> Union[str, None]:
    """
    Determine shader type of material using node types and connections.
    Returns shader type string or None if not detected.
    """
    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree.nodes

    # 1. First try connection-based detection (most robust)
    output_node = find_output_node(node_tree)
    if output_node:
        shader_result = trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result

            # Check if this shader has an image texture connected
            image_node = find_connected_image_node(shader_node, shader_type)
            if image_node:
                return shader_type
            else:
                return f"{shader_type}Col"  # No texture, use color variant

    # 2. Fallback to detection based on node names
    # Group node checks (special cases)
    if 'Group' in node_tree:
        node_tree_name = node_tree['Group'].node_tree.name
        if node_tree_name == 'Group':
            return 'xnalaraNewCol'
        if node_tree_name == 'MToon_unversioned':
            return 'vrm' if 'Image Texture' in node_tree else 'vrmCol'
        elif node_tree_name == 'XPS Shader' and 'Image Texture' in node_tree:
            return 'xnalara'

    # Check for MMD shader specifically
    if MMD_SHADER_NAMES.intersection(node_tree.keys()):
        return 'mmd' if MMD_TEXTURE_NAMES.intersection(node_tree.keys()) else 'mmdCol'

    # Check for MTOON shader specifically
    if MTOON_SHADER_NAMES.intersection(node_tree.keys()):
        return 'mtoon' if MTOON_TEXTURE_NAMES.intersection(node_tree.keys()) else 'mtoonCol'

    # As last resort, check against predefined shader types
    node_names_set = set(node_tree.keys())
    return next(
        (
            shader_type
            for shader_type, node_names in shader_types.items()
            if node_names.issubset(node_names_set)
        ),
        None,
    )


def find_shader_nodes(node_tree) -> List[bpy.types.Node]:
    """Find all shader nodes in a node tree."""
    shader_nodes = []
    for node in node_tree.nodes:
        if node.bl_idname in SHADER_NODE_TYPES or (
            node.bl_idname == 'ShaderNodeGroup' and 
            hasattr(node, 'node_tree') and 
            node.node_tree and 
            node.node_tree.name in SHADER_NODE_TYPES.get('ShaderNodeGroup', {})
        ):
            shader_nodes.append(node)
    return shader_nodes


def find_color_connected_image(node_tree) -> Optional[bpy.types.Image]:
    """
    Find an image that's connected to a color/base color/diffuse socket 
    of any shader node in the material.
    """
    shader_nodes = find_shader_nodes(node_tree)
    
    for shader_node in shader_nodes:
        for input_socket in shader_node.inputs:
            if any(color_term in input_socket.name.lower() for color_term in ['color', 'diffuse', 'base']):
                if input_socket.links:
                    for link in input_socket.links:
                        from_node = link.from_node
                        if is_image_texture_node(from_node):
                            return from_node.image
                        
                        # Try recursive search
                        image_node = find_image_texture_in_node_tree(from_node, set())
                        if image_node and hasattr(image_node, 'image'):
                            return image_node.image
    return None


def get_image_from_material(mat: bpy.types.Material) -> Optional[bpy.types.Image]:
    """Get the main albedo/diffuse image from a material using node-based detection."""
    if not mat.node_tree or not mat.node_tree.nodes:
        return None

    node_tree = mat.node_tree

    # Try connection-based detection first (most reliable)
    output_node = find_output_node(node_tree.nodes)
    if output_node:
        shader_result = trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result
            image_node = find_connected_image_node(shader_node, shader_type)
            if image_node and hasattr(image_node, 'image'):
                return image_node.image

    # Try special case detections
    # MMD-specific detection
    if 'mmd_base_tex' in node_tree.nodes and hasattr(node_tree.nodes['mmd_base_tex'], 'image'):
        return node_tree.nodes['mmd_base_tex'].image
    
    # MToon-specific detection
    if 'Mtoon1BaseColorTexture.Image' in node_tree.nodes and hasattr(node_tree.nodes['Mtoon1BaseColorTexture.Image'], 'image'):
        return node_tree.nodes['Mtoon1BaseColorTexture.Image'].image

    # Find image connected to color inputs of any shader
    color_connected_image = find_color_connected_image(node_tree)
    if color_connected_image:
        return color_connected_image

    # Try to find any image texture node in the tree
    for node in node_tree.nodes:
        if is_image_texture_node(node):
            return node.image

    # Fallback to name-based detection
    shader = get_shader_type(mat)
    if shader and shader in shader_image_nodes:
        node_name = shader_image_nodes[shader]
        if node_name in node_tree.nodes:
            node = node_tree.nodes[node_name]
            if hasattr(node, 'image'):
                return node.image
    
    return None


def rgb_to_255_scale(diffuse: Diffuse) -> Diffuse:
    """Convert RGB float values (0-1) to 8-bit integer values (0-255) with proper gamma correction."""
    rgb = np.empty(shape=(0,), dtype=int)
    for c in diffuse:
        if c < 0.0:
            srgb = 0
        elif c < 0.0031308:
            srgb = c * 12.92
        else:
            srgb = 1.055 * pow(c, 1.0 / 2.4) - 0.055
        rgb = np.append(rgb, np.clip(round(srgb * 255), 0, 255))
    return tuple(rgb)


def get_color_from_shader_node(shader_node: bpy.types.Node, shader_type: str) -> Optional[Tuple[int, int, int, int]]:
    """Extract color from a shader node based on its type."""
    if shader_type == 'principled' and 'Base Color' in shader_node.inputs:
        return rgb_to_255_scale(shader_node.inputs['Base Color'].default_value)
    elif shader_type == 'diffuse' and 'Color' in shader_node.inputs:
        return rgb_to_255_scale(shader_node.inputs['Color'].default_value)
    elif shader_type == 'emission' and 'Color' in shader_node.inputs:
        return rgb_to_255_scale(shader_node.inputs['Color'].default_value)
    return None


def get_diffuse(mat: bpy.types.Material) -> Tuple[int, int, int, int]:
    """
    Get the diffuse color from a material, handling different shader types.
    Returns RGBA values in 0-255 range for Pillow as a 4-element tuple.
    """
    if not mat:
        return 255, 255, 255, 255

    if globs.is_blender_2_79_or_older:
        return rgb_to_255_scale(mat.diffuse_color)

    # For Blender 2.80+, use node-based detection
    if not mat.node_tree or not mat.node_tree.nodes:
        return 255, 255, 255, 255

    # Try connection-based detection first
    output_node = find_output_node(mat.node_tree.nodes)
    if output_node:
        shader_result = trace_connected_shader(output_node)
        if shader_result:
            shader_node, shader_type = shader_result
            color = get_color_from_shader_node(shader_node, shader_type)
            if color:
                return color

    # Fallback to shader-specific detection
    shader = get_shader_type(mat)
    if not shader:
        return 255, 255, 255, 255

    node_tree = mat.node_tree.nodes
    
    # Handle specific shader types
    if shader == 'mmdCol' and 'mmd_shader' in node_tree:
        return rgb_to_255_scale(node_tree['mmd_shader'].inputs['Diffuse Color'].default_value)
    elif shader == 'mtoonCol' and 'Mtoon1PbrMetallicRoughness.BaseColorFactor' in node_tree:
        return rgb_to_255_scale(node_tree['Mtoon1PbrMetallicRoughness.BaseColorFactor'].color)
    elif shader == 'vrm' and 'RGB' in node_tree:
        return rgb_to_255_scale(node_tree['RGB'].outputs[0].default_value)
    elif shader == 'vrmCol' and 'Group' in node_tree:
        return rgb_to_255_scale(node_tree['Group'].inputs[10].default_value)
    elif shader == 'diffuseCol' and 'Diffuse BSDF' in node_tree:
        return rgb_to_255_scale(node_tree['Diffuse BSDF'].inputs['Color'].default_value)
    elif shader == 'xnalaraNewCol' and 'Group' in node_tree:
        return rgb_to_255_scale(node_tree['Group'].inputs['Diffuse'].default_value)
    elif shader in ['principledCol', 'xnalaraCol'] and 'Principled BSDF' in node_tree:
        return rgb_to_255_scale(node_tree['Principled BSDF'].inputs['Base Color'].default_value)
    
    # Default white color if nothing else matches
    return 255, 255, 255, 255


def sort_materials(mat_list: List[bpy.types.Material]) -> ValuesView[MatDictItem]:
    """
    Sort materials by their textures and diffuse colors for combining.
    Groups materials with the same texture/color combinations.
    """
    for mat in bpy.data.materials:
        mat.root_mat = None

    mat_dict = cast(MatDict, defaultdict(list))
    for mat in mat_list:
        if not mat:
            continue

        packed_file = None

        if globs.is_blender_2_79_or_older:
            packed_file = get_packed_file(get_image(get_texture(mat)))
        else:
            image = get_image_from_material(mat)
            if image:
                packed_file = get_packed_file(image)

        # Get diffuse color (always RGBA)
        diffuse_rgba = get_diffuse(mat)

        if packed_file:
            key = (packed_file, diffuse_rgba if mat.smc_diffuse else (255, 255, 255, 255))
            mat_dict[key].append(mat)
        else:
            mat_dict[diffuse_rgba].append(mat)

    return mat_dict.values()
