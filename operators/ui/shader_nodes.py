import bpy
import numpy as np


# Only registered in Blender 2.80+
class SetActiveNodeAsOverride(bpy.types.Operator):
    bl_idname = 'smc.shader_nodes_set_active_as_override'
    bl_label = "Set"
    bl_description = "Set the active node as the material's search override"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        if space_data.type == 'NODE_EDITOR' and space_data.node_tree != space_data.edit_tree:
            # Disable when inside a group node
            return False
        # When context is the shader node window, it has a material attribute of the current (possibly pinned) material
        # and has easy access to the active node
        return (hasattr(context, 'material')
                and hasattr(context, 'active_node')
                # Active material must not be None
                and context.material
                # Active node must not be None
                and context.active_node
                # The active node only shows as active in the UI when it is selected so .select must be checked too
                and context.active_node.select
                # The active node could be in a group node, only nodes in the material are allowed
                and context.active_node.id_data == context.material.node_tree)

    def execute(self, context):
        mat = context.material
        mat.smc_override_node_name = mat.node_tree.nodes.active.name
        return {'FINISHED'}


# Only registered in Blender 2.80+
class SetOverrideAsActive(bpy.types.Operator):
    bl_idname = 'smc.shader_nodes_set_override_as_active'
    bl_label = "Select"
    bl_description = "Select the material's search override as active"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        if space_data.type == 'NODE_EDITOR' and space_data.node_tree != space_data.edit_tree:
            # Disable when inside a group node
            return False
        # When context is the shader node window, it has a material attribute of the current (possibly pinned) material
        if hasattr(context, 'material'):
            mat = context.material
            if mat:
                node_tree = mat.node_tree
                if node_tree:
                    nodes = node_tree.nodes
                    if nodes:
                        return mat.smc_override_node_name in nodes
        return False

    def execute(self, context):
        mat = context.material
        nodes = mat.node_tree.nodes
        override_node = nodes[mat.smc_override_node_name]
        override_node.select = True
        nodes.active = override_node
        return {'FINISHED'}


# Only registered in Blender 2.80+
class ClearOverride(bpy.types.Operator):
    bl_idname = 'smc.shader_nodes_clear_override'
    bl_label = "Clear"
    bl_description = "Clear the material's search override"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        # When context is the shader node window, it has a material attribute of the current (possibly pinned) material
        if hasattr(context, 'material'):
            mat = context.material
            return mat.smc_override_node_name
        return False

    def execute(self, context):
        context.material.smc_override_node_name = ''
        return {'FINISHED'}


# Only registered in Blender 2.80+
class FrameOverride(bpy.types.Operator):
    bl_idname = 'smc.shader_nodes_frame_override'
    bl_label = "View"
    bl_description = "Resize view so you can see the search override node"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        # Must be in a node_editor and not be inside a group node.
        # .edit_tree will be the current tree, whereas .node_tree will be the tree of the current material
        if space_data.type == 'NODE_EDITOR' and space_data.node_tree == space_data.edit_tree:
            # When context is the shader node window, it has a material attribute of the current (possibly pinned)
            # material
            if hasattr(context, 'material'):
                mat = context.material
                if mat:
                    node_tree = mat.node_tree
                    if node_tree:
                        nodes = node_tree.nodes
                        if nodes:
                            # A node with name matching the override node name must exist
                            return mat.smc_override_node_name in nodes
        return False

    def execute(self, context):
        return bpy.ops.smc.shader_nodes_frame_node(node_name=context.material.smc_override_node_name)


# Only registered in Blender 2.80+
class FrameNode(bpy.types.Operator):
    bl_idname = 'smc.shader_nodes_frame_node'
    bl_label = "View"
    bl_description = "Resize view so you can see the specified node"

    node_name = bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        # Must be in a node_editor.
        # .edit_tree will be the current tree, whereas .node_tree will be the tree of the current material
        if space_data.type == 'NODE_EDITOR':
            # When context is the shader node window, it has a material attribute of the current (possibly pinned)
            # material
            if hasattr(context, 'material'):
                node_tree = space_data.edit_tree
                if node_tree:
                    return node_tree.nodes
        return False

    def execute(self, context):
        nodes = context.space_data.edit_tree.nodes
        if self.node_name in nodes:
            # Create array that we can write the current selection state to
            old_select = np.empty(len(nodes), dtype=bool)
            # Get current selection so we can restore it
            nodes.foreach_get('select', old_select)
            # Clear selection
            nodes.foreach_set('select', np.zeros(len(nodes), dtype=bool))
            # Select the node
            node = nodes[self.node_name]
            node.select = True
            # View only the selected nodes (which is now only the node we want)
            bpy.ops.node.view_selected()
            # Restore the selection
            nodes.foreach_set('select', old_select)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}
