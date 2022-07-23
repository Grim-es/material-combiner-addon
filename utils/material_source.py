from collections import namedtuple
import numpy as np

import bpy
from bpy.types import bpy_prop_collection, Image, ShaderNode, ShaderNodeTree, ShaderNodeGroup, NodeSocketColor, Material

from .images import is_single_colour_generated, single_color_generated_to_color
from .textures import get_image, get_texture
from ..globs import debug_print


# Could create the PropTuple class using namedtuple(...) separately and then add the resolve method to it
# afterwards, but it confuses PyCharm into thinking the method doesn't exist, so the method has been added to a subclass
# with the namedtuple class as a superclass.
class PropTuple(namedtuple('PropTupleBase', ['prop_holder', 'path'])):
    def resolve(self):
        return self.prop_holder.path_resolve(self.path)


def to_255_scale_tuple(rgba):
    # Convert to unsigned char (unsigned byte)
    # This is the same conversion Blender uses internally, as defined in unit_float_to_uchar_clamp in
    # math_base_inline.c, albeit vectorized for numpy. It doesn't really need to be vectorized since colors are only
    # 4 values, but this was leftover code from previously using ImBuf to write pixels to an Image faster.
    rgba = np.array(rgba, dtype=np.single)
    condition_list = [rgba <= np.single(0.0), rgba > (np.single(1.0) - np.single(0.5) / np.single(255.0))]
    choice_list = [np.single(0.0), np.single(255.0)]
    default_value = np.single(255.0) * rgba + np.single(0.5)
    return tuple(np.select(condition_list, choice_list, default=default_value).astype(np.ubyte))


class MaterialSource:
    # Name of the Image Texture node to use as an override when getting a Material's Image
    image_override_name = "MaterialCombinerOverride"

    # Used when trying to get a color value from a material that has no color
    # This is the multiplicative identity, i.e., multiplying a pixel by it does nothing
    opaque_white = (1, 1, 1, 1)

    # The different types of renderer targets for material output nodes
    # They will be iterated in the order specified in this list
    output_node_targets = ['ALL', 'EEVEE', 'CYCLES']

    # The very initial support of Blender 2.8 in mmd_tools appears to have used PrincipledBSDF. Shortly after, it was
    #   replaced with a group node with the same Diffuse Color and Base Tex inputs as used at the time of writing
    mmd_group_name = 'MMDShaderDev'
    mmd_color_input_name = 'Diffuse Color'
    mmd_image_input_name = 'Base Tex'

    # The vrm addon stores the MToon_unversioned node group in a blend file, loads it as a library and then adds the
    #   group node from it to the current blend file
    # Previously, all three groups were stored in a single material_node_groups.blend, see
    #   https://github.com/saturday06/VRM_Addon_for_Blender/commit/e75cd6211795e6b16dccea886f5357ea1bf97f3a
    # Most, older changes can be found via
    #   https://github.com/saturday06/VRM_Addon_for_Blender/commits/697ce4b2003e058e67aa4228468c579c2f8ac3db/resources/material_node_groups.blend
    # See V_Types.py for any changes to group node inputs, e.g.
    #   https://github.com/saturday06/VRM_Addon_for_Blender/blob/f3ac133b0cd4c43c0e9a2f4833ef62f3af2c30cc/V_Types.py
    # DiffuseColor and MainTexture were added super early and haven't changed as of the time of writing
    #   https://github.com/saturday06/VRM_Addon_for_Blender/commit/b9559e9f465a2181e3093d66609c8363b53d4e41
    vrm_group_name = 'MToon_unversioned'
    vrm_color_input_name = 'DiffuseColor'
    vrm_image_input_name = 'MainTexture'

    # In the future, we could add in alpha for some node setups so that, a specific alpha value can be used instead of
    # assuming 1.0.
    # Maybe the Image could also be replaced with a PropTuple.
    def __init__(self, image: Image = None, color: PropTuple = None):
        self.image = image
        self.color = color

    def __repr__(self):
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    # A MaterialSource is only considered valid if it has at least one of image or color
    def __bool__(self):
        if self.image or self.color:
            return True
        else:
            return False

    # Used for comparison (specifically uniqueness and sorting)
    # All colors must be converted to the same colorspace in order to be compared. Since colors from shader nodes are
    # already in scene linear colorspace it's less work to convert only the single_color_generated images that are in
    # sRGB to Linear.
    def to_sort_key(self, multiply_by_diffuse: bool):
        if self.image:
            if is_single_colour_generated(self.image):
                target_colorspace = 'Linear'
                if multiply_by_diffuse:
                    if self.color:
                        combined_converted_color = single_color_generated_to_color(self.image, self.to_color_value(),
                                                                                   target_colorspace=target_colorspace)
                        return '', to_255_scale_tuple(combined_converted_color)
                    else:
                        converted_color = single_color_generated_to_color(self.image,
                                                                          target_colorspace=target_colorspace)
                        return '', to_255_scale_tuple(converted_color)
                else:
                    converted_color = single_color_generated_to_color(self.image, target_colorspace=target_colorspace)
                    return '', to_255_scale_tuple(converted_color)
            else:
                if multiply_by_diffuse:
                    return self.image.name, to_255_scale_tuple(self.to_color_value())
                else:
                    return self.image.name, MaterialSource.opaque_white
        else:
            # Images can't be named '', so '' works to indicate that there is no image
            return '', to_255_scale_tuple(self.to_color_value())

    def to_color_value(self):
        if self.color:
            color_value = tuple(self.color.resolve())
            if len(color_value) < 4:
                # Blender 2.79 internal renderer material diffuse color is only RGB, so append Alpha of 1
                color_value = tuple(color_value + (1,) * (len(color_value) - 4))
            else:
                # Shader node colors are RGBA, but only use RGB so
                color_value = color_value[:3] + (1,)
            return color_value
        else:
            return MaterialSource.opaque_white

    @staticmethod
    def merge_color_and_tex(color_source: 'MaterialSource', tex_source: 'MaterialSource'):
        if color_source:
            if tex_source:
                # Preferably pick the image from tex_source and the color from color_source
                image = tex_source.image if tex_source.image else color_source.image
                color = color_source.color if color_source.color else tex_source.color
                return MaterialSource(image=image, color=color)
            else:
                return color_source
        elif tex_source:
            return tex_source
        else:
            # Neither have an image nor color, so it doesn't matter which we return
            return color_source

    @staticmethod
    def from_node_tree(node_tree: ShaderNodeTree):
        source_data = MaterialSource.from_override(node_tree.nodes)
        if source_data:
            return source_data
        # Get the output nodes for all renderer targets.
        # If no node exists with a particular target, None will be returned by get_output_node.
        # An 'ALL' node can also be retrieved when getting 'EEVEE' and/or 'CYCLES' nodes, resulting in duplicates.
        material_output_node_gen = (node_tree.get_output_node(target) for target in MaterialSource.output_node_targets)
        # Filter out output nodes that don't exist
        material_output_node_gen = filter(bool, material_output_node_gen)
        # Remove any duplicates, but maintain order by making a dict.
        # Note that this code is only run on Blender 2.80+ which uses Python 3.7+ where dictionaries are guaranteed to
        # preserve insertion order.
        node_tree_outputs = dict.fromkeys(material_output_node_gen).keys()

        for output_node in node_tree_outputs:
            source_data = MaterialSource.from_node(output_node)
            if source_data:
                return source_data
        # As a last ditch attempt, if there is only one Image Texture node in the material, use that.
        return MaterialSource.from_singular_image_texture_node(node_tree.nodes)

    @staticmethod
    def from_override(nodes: bpy_prop_collection):
        override_node = nodes.get(MaterialSource.image_override_name)
        if override_node:
            return MaterialSource.from_node(override_node)
        else:
            return MaterialSource()

    @staticmethod
    def from_singular_image_texture_node(nodes: bpy_prop_collection):
        found_node = None
        for node in nodes:
            # If node is an Image Texture node, and it has an image assigned
            if node.type == 'TEX_IMAGE' and node.image:
                if found_node is not None:
                    # Already found one previously, so there is more than one Image Texture node.
                    return MaterialSource()
                found_node = node
        if found_node:
            return MaterialSource.from_node(found_node)
        else:
            return MaterialSource()

    @staticmethod
    def from_node(node: ShaderNode):
        if node.type == 'OUTPUT_MATERIAL':
            surface_input = node.inputs['Surface']
            if surface_input.is_linked:
                link = surface_input.links[0]
                if link.is_valid:
                    return MaterialSource.from_node(link.from_node)
        elif node.type == 'TEX_IMAGE':
            if node.image:
                return MaterialSource(image=node.image)
        elif node.type == 'RGB':
            return MaterialSource(color=PropTuple(node.outputs[0], 'default_value'))
        elif node.type in {'BSDF_PRINCIPLED', 'EEVEE_SPECULAR'}:
            return MaterialSource.from_color_input_socket(node.inputs['Base Color'])
        elif node.type in {'Emission', 'BSDF_DIFFUSE', 'BSDF_GLASS', 'BSDF_GLOSSY', 'BSDF_REFRACTION',
                           'SUBSURFACE_SCATTERING', 'BSDF_TRANSLUCENT', 'BSDF_TRANSPARENT'}:
            # BSDF_GLASS, BSDF_REFRACTION and BSDF_TRANSPARENT may produce unexpected results
            # The strength value in Emission is ignored
            return MaterialSource.from_color_input_socket(node.inputs['Color'])
        elif node.type == 'GROUP':
            return MaterialSource.from_group_node(node)
        elif node.type == 'MIX_SHADER':
            # If a Mix Shader node's Fac input is set to 0 or 1, we can follow the corresponding links to nodes
            fac_input = node.inputs['Fac']
            if not fac_input.is_linked:
                if fac_input.default_value == 0:
                    first_shader_input = node.inputs[1]
                    if first_shader_input.is_linked:
                        link = first_shader_input.links[0]
                        if link.is_valid:
                            return MaterialSource.from_node(link.from_node)
                elif fac_input.default_value == 1:
                    second_shader_input = node.inputs[2]
                    if second_shader_input.is_linked:
                        link = second_shader_input.links[0]
                        if link.is_valid:
                            return MaterialSource.from_node(link.from_node)
        return MaterialSource()

    @staticmethod
    def from_color_input_socket(input_socket: NodeSocketColor):
        if input_socket.is_linked:
            link = input_socket.links[0]
            if link.is_valid:
                return MaterialSource.from_node(input_socket.links[0].from_node)
            else:
                return MaterialSource()
        else:
            return MaterialSource(color=PropTuple(input_socket, 'default_value'))

    @staticmethod
    def from_group_color_input_socket(group_node: ShaderNodeGroup, socket_name: str):
        socket = group_node.inputs.get(socket_name)
        if isinstance(socket, NodeSocketColor):
            return MaterialSource.from_color_input_socket(socket)
        else:
            print("Unable to find {} input of {} group node {}. Perhaps the addon the group node is from has been"
                  " updated or the group node has been modified by the user"
                  .format(socket_name, group_node.node_tree.name, group_node))
            return MaterialSource()

    @staticmethod
    def from_image_and_color_group_inputs(group_node: ShaderNodeGroup, color_input_name: str, image_input_name: str):
        color_source = MaterialSource.from_group_color_input_socket(group_node, color_input_name)
        tex_source = MaterialSource.from_group_color_input_socket(group_node, image_input_name)
        return MaterialSource.merge_color_and_tex(color_source, tex_source)

    @staticmethod
    def from_group_node(group_node: ShaderNodeGroup):
        node_tree_name = group_node.node_tree.name
        if node_tree_name == MaterialSource.mmd_group_name:
            return MaterialSource.from_image_and_color_group_inputs(
                group_node, MaterialSource.mmd_color_input_name, MaterialSource.mmd_image_input_name)
        elif node_tree_name == MaterialSource.vrm_group_name:
            return MaterialSource.from_image_and_color_group_inputs(
                group_node, MaterialSource.vrm_color_input_name, MaterialSource.vrm_image_input_name)
        else:
            print("Unsupported group node for getting MaterialSource {}".format(node_tree_name))
            return MaterialSource()

    @staticmethod
    def from_material(mat: Material):
        debug_print("DEBUG: Getting material source data for {}".format(mat))
        if mat:
            if bpy.app.version >= (2, 80):
                if mat.use_nodes:
                    return MaterialSource.from_node_tree(mat.node_tree)
                else:
                    return MaterialSource(color=PropTuple(mat, 'diffuse_color'))
            else:
                image = get_image(get_texture(mat))
                prop_holder = mat
                prop_name = 'diffuse_color'
                return MaterialSource(image=image, color=PropTuple(prop_holder, prop_name))
        else:
            return MaterialSource()
