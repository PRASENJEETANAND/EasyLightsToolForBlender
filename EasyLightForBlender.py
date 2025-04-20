bl_info = {
    "name": "Easy Light Tool",
    "author": "Prasenjeet Anand",
    "version": (2, 5),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Light Groups",
    "description": "Assign lights to groups, control attributes, update lightgroup with AOV check",
    "category": "Lighting",
}

import bpy
import re

class LightGroupSettings(bpy.types.PropertyGroup):
    skip_existing: bpy.props.BoolProperty(
        name="Skip Existing Assignments",
        description="Skip lights that already have a light group assigned",
        default=True
    )
    use_lg_grouping: bpy.props.BoolProperty(
        name="Group by LG_ Tag",
        description="Use shared light group based on name after 'LG_'",
        default=False
    )
    add_to_aov_if_missing: bpy.props.BoolProperty(
        name="Add to AOV if Missing",
        description="Automatically create the AOV if the light group is missing",
        default=False
    )

    selected_light: bpy.props.PointerProperty(
        name="Light",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'LIGHT'
    )


class OBJECT_OT_assign_light_groups_b44(bpy.types.Operator):
    bl_idname = "object.assign_light_groups_b44"
    bl_label = "Assign Light Groups"
    bl_description = "Assign lights to light groups by name or LG_ tag and create AOVs"

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        settings = scene.light_group_settings

        if scene.render.engine != 'CYCLES':
            self.report({'ERROR'}, "Cycles render engine is required.")
            return {'CANCELLED'}

        count, skipped, aovs_created = 0, 0, 0

        for obj in scene.objects:
            if obj.type != 'LIGHT':
                continue

            if settings.skip_existing and obj.lightgroup:
                skipped += 1
                continue

            group_name = obj.name
            if settings.use_lg_grouping:
                match = re.search(r"LG_(\w+)", obj.name)
                if match:
                    group_name = match.group(1)

            obj.lightgroup = group_name
            count += 1

            if group_name not in [aov.name for aov in view_layer.lightgroups]:
                view_layer.lightgroups.add(name=group_name)
                aovs_created += 1

        self.report({'INFO'}, f"Assigned {count} lights, skipped {skipped}, created {aovs_created} AOVs.")
        return {'FINISHED'}


class OBJECT_OT_select_light_in_outliner(bpy.types.Operator):
    bl_idname = "object.select_light_in_outliner"
    bl_label = "Select Light in Outliner"
    bl_description = "Select the light in the scene and focus in Outliner"

    def execute(self, context):
        light = context.scene.light_group_settings.selected_light
        if light:
            bpy.ops.object.select_all(action='DESELECT')
            light.select_set(True)
            context.view_layer.objects.active = light
            self.report({'INFO'}, f"Selected light: {light.name}")
        return {'FINISHED'}


class OBJECT_OT_update_lightgroup(bpy.types.Operator):
    bl_idname = "object.update_lightgroup"
    bl_label = "Update Light Group"
    bl_description = "Update the light group of the selected light and add AOV if needed"

    def execute(self, context):
        settings = context.scene.light_group_settings
        light = settings.selected_light
        view_layer = context.view_layer

        if not light or light.type != 'LIGHT':
            self.report({'WARNING'}, "No light selected or invalid type")
            return {'CANCELLED'}

        group_name = light.lightgroup.strip()
        if not group_name:
            self.report({'WARNING'}, "Light group name is empty")
            return {'CANCELLED'}

        # Check if group exists in AOVs
        if group_name in [aov.name for aov in view_layer.lightgroups]:
            self.report({'INFO'}, f"Light group '{group_name}' already exists. Updated.")
        elif settings.add_to_aov_if_missing:
            view_layer.lightgroups.add(name=group_name)
            self.report({'INFO'}, f"Light group '{group_name}' added to AOVs.")
        else:
            self.report({'ERROR'}, f"'{group_name}' does not exist in AOVs. Enable 'Add to AOV if Missing' to create it.")
            return {'CANCELLED'}

        return {'FINISHED'}


class VIEW3D_PT_light_group_panel_b44(bpy.types.Panel):
    bl_label = "Light Groups Assignment"
    bl_idname = "VIEW3D_PT_light_groups_b44"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Easy Light Tool'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.light_group_settings

        # "Easy LightGroup" logo style
        row = layout.row()
        row.scale_y = 1.6
        row.label(text="EASY LIGHTGROUP", icon='LIGHT')

        layout.separator()
        layout.label(text="Light Group Assignment:")
        layout.prop(settings, "skip_existing")
        layout.prop(settings, "use_lg_grouping")
        layout.operator("object.assign_light_groups_b44", icon='LIGHT')


class VIEW3D_PT_light_control_panel(bpy.types.Panel):
    bl_label = "Light Control Panel"
    bl_idname = "VIEW3D_PT_light_control_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Easy Light Tool'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.light_group_settings
        light = settings.selected_light

        layout.label(text="Select Light to Edit:")
        layout.prop(settings, "selected_light", text="")

        if light and light.type == 'LIGHT':
            layout.operator("object.select_light_in_outliner", icon='RESTRICT_SELECT_OFF')

            light_data = light.data
            layout.prop(light_data, "color", text="Color")
            layout.prop(light_data, "energy", text="Power")
            if hasattr(light_data, "shadow_soft_size"):
                layout.prop(light_data, "shadow_soft_size", text="Size")
            if light_data.type == 'SPOT':
                layout.prop(light_data, "spot_size", text="Spot Angle")
                layout.prop(light_data, "spot_blend", text="Spot Blend")

            layout.separator()
            layout.label(text="Light Group:")
            layout.prop(light, "lightgroup", text="Group")
            layout.prop(settings, "add_to_aov_if_missing")
            layout.operator("object.update_lightgroup", icon='FILE_REFRESH')


classes = [
    LightGroupSettings,
    OBJECT_OT_assign_light_groups_b44,
    OBJECT_OT_select_light_in_outliner,
    OBJECT_OT_update_lightgroup,
    VIEW3D_PT_light_group_panel_b44,
    VIEW3D_PT_light_control_panel,
]

class OBJECT_OT_rename_dots(bpy.types.Operator):
    bl_idname = "object.rename_dots"
    bl_label = "Replace . with _"
    bl_description = "Rename all objects by replacing '.' with '_'"
    bl_options = {'REGISTER', 'UNDO'}



    def execute(self, context):
        for obj in bpy.data.objects:
            if "." in obj.name:
                new_name = obj.name.replace(".", "_")
                obj.name = new_name
        self.report({'INFO'}, "Renamed objects with '.' to '_'")
        return {'FINISHED'}

class OBJECT_PT_rename_panel(bpy.types.Panel):
    bl_label = "Fix Light Name "
    bl_idname = "OBJECT_PT_rename_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Light Tool"
    bl_options = {'DEFAULT_CLOSED'}


    
    def draw(self, context):
        layout = self.layout
        layout.operator("object.rename_dots")


class OBJECT_PT_rename_info_panel(bpy.types.Panel):
    bl_label = "Read it Before USE"                 # Title shown in the panel
    bl_idname = "OBJECT_PT_rename_info_panel"    # Unique ID
    bl_space_type = 'VIEW_3D'                    # Show in 3D Viewport
    bl_region_type = 'UI'                        # Show in N-panel (UI region)
    bl_category = "Easy Light Tool"                    # Same tab as other tools
    bl_order = 0                                 # Optional: Makes it appear first if supported

    def draw(self, context):
        layout = self.layout
        box = layout.box()  # Boxed message
        box.label(text="EXPAND THIS PANEL PLEASE")
        box.label(text="This tool is for creating Light group with easy")
        box.label(text="• Also this will help other tools work properly")
        box.label(text="  So we are replacing it with underscore (_).")
        box.label(text="  Fix Light name Pannel is necessary because")
        box.label(text="  Blender donot support dot (.) in lightGroup names")
        box.label(text="• Light Groups Assignment")
        box.label(text="  - automatic create light group based on light name")
        box.label(text="  - If groub by tag enabled, it can group them too")
        box.label(text="• Light Control Pannel will give necessary control from scenes for light")
        


def register():
    bpy.utils.register_class(OBJECT_PT_rename_info_panel)
    bpy.utils.register_class(OBJECT_OT_rename_dots)
    bpy.utils.register_class(OBJECT_PT_rename_panel)
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.light_group_settings = bpy.props.PointerProperty(type=LightGroupSettings)

def unregister():
    bpy.utils.unregister_class(OBJECT_PT_rename_info_panel)
    bpy.utils.register_class(OBJECT_OT_rename_dots)
    bpy.utils.register_class(OBJECT_PT_rename_panel)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.light_group_settings

if __name__ == "__main__":
    register()
