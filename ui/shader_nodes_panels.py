import bpy
from ..utils import material_source
from ..utils import images


def get_node_display_label(node):
    if node.label:
        return node.label
    # Custom nodes can define a draw_label function
    elif hasattr(node, 'draw_label'):
        return node.draw_label()
    # Image Texture nodes display the name of their .image
    elif node.type == 'TEX_IMAGE' and node.image:
        return node.image.name
    # Group nodes display the name of their .node_tree
    elif node.type == 'GROUP' and node.node_tree:
        return node.node_tree.name
    else:
        return node.bl_label


# Only registered in Blender 2.80+
class ShaderNodesSourcePreviewPanel(bpy.types.Panel):
    bl_label = "Material Sources"
    bl_idname = 'SMC_PT_Shader_Nodes_Source_Preview'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "MatCombiner"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        # Don't need to check for context.space_data.type == 'NODE_EDITOR' because it's the Panel's bl_space_type
        space_data = context.space_data
        # Only show the panel in the shader nodes window and only if the current material has nodes.
        if space_data.tree_type == 'ShaderNodeTree':
            if hasattr(context, 'material'):
                mat = context.material
                if mat:
                    node_tree = mat.node_tree
                    if node_tree:
                        return node_tree.nodes
        return False

    @staticmethod
    def draw_prop_holder(context, layout, prop_tuple, source_name):
        layout.label(text=source_name + ":")
        box = layout.box()
        prop_holder = prop_tuple.prop_holder

        if isinstance(prop_holder, bpy.types.ShaderNode):
            node = prop_holder
        elif isinstance(prop_holder, bpy.types.NodeSocket):
            node = prop_holder.node
        else:
            node = None

        if node:
            # When there's a node, we change the icon according to whether the node is selected (and in the current
            # edit_tree) and we add a button to focus the view on the node
            node_in_current_tree = context.space_data.edit_tree == node.id_data
            row = box.row()
            row.label(text="{}".format(get_node_display_label(node)),
                      icon='NODE_SEL' if node_in_current_tree and node.select else 'NODE')
            # The operator can't disable itself based on its node_name argument because the poll method is a classmethod
            # Instead, we'll disable the UI when we know the node isn't in the current edit_tree
            # To disable only the operator button we need to put it in its own sub-layout, so create a column for it
            col = row.column()
            col.enabled = node_in_current_tree
            col.operator('smc.shader_nodes_frame_node', icon='VIEWZOOM', text='').node_name = node.name
        else:
            icon = 'MATERIAL' if isinstance(prop_holder, bpy.types.Material) else 'BLANK1'
            if hasattr(prop_holder, 'name'):
                # .name is likely to be a string, but cast to be sure
                text = str(prop_holder.name)
            elif hasattr(prop_holder, 'path_from_id'):
                # .path_from_id() is likely to be a string, but cast to be sure
                text = str(prop_holder.path_from_id())
            else:
                # Generally a prop_holder will have at least one of name or path_from_id. For anything else, get the
                # string representation.
                # str() usually prints pointer and not much useful info, so use repr()
                text = repr(prop_holder)
            box.label(text=text, icon=icon)
        # Placing Color props directly into the box puts the property name and color UI on different lines for some
        # reason. Creating a row in the box and putting the prop in that row keeps them both on the same line.
        row = box.row()
        # Usually we want to display the name of the property in the UI (typically the default text used when set to
        # None), but when the prop_holder is a NodeSocket, the property is usually 'default_value' which isn't very
        # useful, instead, the name of the socket is more useful, especially since when prop_holder is a socket, we
        # display the node it belongs to instead of the socket itself.
        text = prop_holder.name if isinstance(prop_holder, bpy.types.NodeSocket) else None
        row.prop(prop_holder, prop_tuple.path, text=text)
        prop = prop_tuple.resolve()
        # Extra UI for generated_color for blank generated images without pending changes
        if isinstance(prop, bpy.types.Image) and images.is_single_colour_generated(prop):
            # As with before, placing the Color prop directly in the box puts the name and color UI on different lines
            # for some reason. Placing it in a row in the box seems to work though.
            row = box.row()
            row.prop(prop, 'generated_color')

    def draw(self, context):
        layout = self.layout

        mat = context.material
        mat_src = material_source.MaterialSource.from_material(mat)
        if mat_src:
            img_prop = mat_src.image
            # If there is an image, it will always be the Base color source so place it before a color
            if img_prop:
                ShaderNodesSourcePreviewPanel.draw_prop_holder(context, layout, img_prop, "Base color")
            color_prop = mat_src.color
            # If there's no image, the color will be used as Base color, otherwise, it will be used as Diffuse color,
            # which optionally multiplies with the Base color during atlas creation
            if color_prop:
                ShaderNodesSourcePreviewPanel.draw_prop_holder(
                    context, layout, color_prop, "Diffuse color" if img_prop else "Base color")
        else:
            layout.label(text="No material source(s) found", icon='ERROR')
            # Blank icons are used to keep the same spacing
            if mat.smc_override_node_name:
                layout.label(text="Try changing the override", icon='BLANK1')
            else:
                layout.label(text="Try setting an override", icon='BLANK1')


# Only registered in Blender 2.80+
class ShaderNodesOverridePanel(bpy.types.Panel):
    bl_label = "Search Start Override"
    bl_idname = 'SMC_PT_Shader_Nodes_Override'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "MatCombiner"
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        # Don't need to check for context.space_data.type == 'NODE_EDITOR' because it's the Panel's bl_space_type
        space_data = context.space_data
        # Only show the panel in the shader nodes window and only if the current material has nodes.
        if space_data.tree_type == 'ShaderNodeTree':
            if hasattr(context, 'material'):
                mat = context.material
                if mat:
                    node_tree = mat.node_tree
                    if node_tree:
                        return node_tree.nodes
        return False

    def draw(self, context):
        mat = context.material
        layout = self.layout
        if not mat.use_nodes:
            layout.label(text="Material does not use nodes")
            layout.prop(mat, "use_nodes", icon='NODETREE')
        else:
            col = layout.column(align=True)
            row = col.row(align=True)
            # SET
            # draw button to set active node to material combiner override
            row.operator('smc.shader_nodes_set_active_as_override')
            # CLEAR
            # draw button to clear the material combiner override
            row.operator('smc.shader_nodes_clear_override')

            row = col.row(align=True)
            # SELECT
            # draw button to select material combiner override (the operator should disable the button via its poll
            #   function when there is no current override)
            row.operator('smc.shader_nodes_set_override_as_active')
            # VIEW
            # draw button to frame (view) the material combiner override
            row.operator('smc.shader_nodes_frame_override')

            override_name = mat.smc_override_node_name
            # Acts as a layout.separator(), but sometimes we later decide to add labels here
            col_pre = layout.column()
            layout.label(text="Override node:")
            box = layout.box()
            if override_name:
                node_tree = mat.node_tree
                override_node = node_tree.nodes.get(mat.smc_override_node_name)
                if override_node:
                    # Display the same displayed label of the node as an expandable header
                    wm = context.window_manager
                    box.prop(wm, "smc_override_node_toggle_full_view", emboss=False,
                             icon="TRIA_DOWN" if wm.smc_override_node_toggle_full_view else "TRIA_RIGHT",
                             text=get_node_display_label(override_node))
                    # If expanded show the full view of the node
                    if wm.smc_override_node_toggle_full_view:
                        # Draw the node in the same way as the Surface panel in Material Properties, but without the input
                        # the override_node's output is connected to
                        box.template_node_view(mat.node_tree, override_node, None)
                    mat_src = material_source.MaterialSource.from_node(override_node)
                    if not mat_src:
                        # Add labels before the override node because any labels or other UI below the node are likely
                        # to be hidden from view when the full view of the node is shown
                        col_pre.label(text="No sources found from override", icon='ERROR')
                        col_pre.label(text="Using active output node(s)", icon='INFO')
                else:
                    col_pre.label(text="Override not found", icon='ERROR')
                    col_pre.label(text="Using active output node(s)", icon='INFO')
                    box.enabled = False
                    box.label(text="'{}' not found".format(override_name), icon='REMOVE')
            else:
                col_pre.label(text="No override set", icon='INFO')
                col_pre.label(text="Using active output node(s)", icon='BLANK1')
                box.enabled = False
                box.label(icon='REMOVE')
