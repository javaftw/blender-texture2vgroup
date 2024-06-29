import bpy
import numpy as np
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "Vertex Group from Texture",
    "author": "Hennie Kotze",
    "version": (1, 8),
    "blender": (4, 1, 0),
    "location": "Properties > Object Data Properties > Vertex Groups",
    "description": "Create vertex groups based on greyscale texture",
    "category": "Mesh",
}

class VGBT_OT_create_groups(bpy.types.Operator, ImportHelper):
    bl_idname = "mesh.create_vertex_groups_from_texture"
    bl_label = "Create Vertex Groups from Texture"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default='*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    texture_source: EnumProperty(
        name="Texture Source",
        description="Choose the source of the texture",
        items=[
            ('EXISTING', "Existing Texture", "Use an existing texture in the scene"),
            ('NEW', "New Texture", "Load a new texture from file"),
        ],
        default='EXISTING'
    )

    texture_name: StringProperty(
        name="Existing Texture",
        description="Choose an existing texture to use for vertex groups",
        default=""
    )

    use_weights: BoolProperty(
        name="Use as Weights",
        description="Treat grey levels as weights for a single vertex group",
        default=False
    )

    weight_group_name: StringProperty(
        name="Weight Group Name",
        description="Name of the vertex group when using weights",
        default="Texture_Weights"
    )

    normalize_weights: BoolProperty(
        name="Normalize Weights",
        description="Normalize weights to full 0-1 range",
        default=False
    )

    num_clusters: IntProperty(
        name="Number of Groups",
        description="Number of vertex groups to create",
        default=64,
        min=2,
        max=256
    )

    min_group_size: IntProperty(
        name="Minimum Group Size",
        description="Minimum number of vertices required to create a group",
        default=10,
        min=1
    )

    base_group_name: StringProperty(
        name="Base Group Name",
        description="Base name for the vertex groups (will be followed by a number)",
        default="group"
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'MESH'

    def invoke(self, context, event):
        self.texture_name = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "texture_source")
        
        if self.texture_source == 'EXISTING':
            layout.prop_search(self, "texture_name", bpy.data, "images")
        else:
            layout.prop(self, "filepath")
        
        layout.prop(self, "use_weights")
        
        if self.use_weights:
            layout.prop(self, "weight_group_name")
            layout.prop(self, "normalize_weights")
        else:
            layout.prop(self, "num_clusters")
            layout.prop(self, "min_group_size")
            layout.prop(self, "base_group_name")

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        if self.texture_source == 'EXISTING':
            if not self.texture_name:
                self.report({'ERROR'}, "No texture selected")
                return {'CANCELLED'}
            image = bpy.data.images[self.texture_name]
        else:
            if not self.filepath:
                self.report({'ERROR'}, "No file selected")
                return {'CANCELLED'}
            image = bpy.data.images.load(self.filepath)
        
        try:
            if self.use_weights:
                success = assign_weights_from_texture(context.object, image, self.weight_group_name, self.normalize_weights)
                if success:
                    self.report({'INFO'}, f"Created vertex group '{self.weight_group_name}' with weights from texture")
                else:
                    self.report({'ERROR'}, "Failed to create vertex group. Check UV mapping.")
            else:
                unique_colors = analyze_texture(image)
                quantized_colors = quantize_colors(unique_colors, self.num_clusters)
                threshold = 1 / (2 * self.num_clusters)  # Automatically calculate threshold
                success = assign_vertex_groups(context.object, quantized_colors, image, threshold, self.min_group_size, self.base_group_name)
                if success:
                    self.report({'INFO'}, f"Created vertex groups based on texture")
                else:
                    self.report({'ERROR'}, "Failed to create vertex groups. Check UV mapping.")
            return {'FINISHED'} if success else {'CANCELLED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class VGBT_PT_main_panel(bpy.types.Panel):
    bl_label = "Vertex Group by Texture"
    bl_idname = "VGBT_PT_main_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.create_vertex_groups_from_texture")

def analyze_texture(image):
    pixels = np.array(image.pixels[:])
    width, height, channels = image.size[0], image.size[1], image.channels
    pixels = pixels.reshape((height, width, channels))
    greyscale = np.mean(pixels[:, :, :3], axis=2) if channels > 1 else pixels[:, :, 0]
    return np.unique(greyscale)

def quantize_colors(colors, num_clusters):
    min_color, max_color = np.min(colors), np.max(colors)
    bins = np.linspace(min_color, max_color, num_clusters + 1)
    quantized_colors = (np.digitize(colors, bins) - 1) / (num_clusters - 1)
    return np.unique(quantized_colors)

def assign_vertex_groups(obj, unique_colors, image, threshold, min_group_size, base_group_name):
    mesh = obj.data
    if not mesh.uv_layers.active:
        raise ValueError("No active UV map found. Please ensure the object has an active UV map.")

    uv_layer = mesh.uv_layers.active.data
    width, height = image.size
    pixels = np.array(image.pixels[:]).reshape((height, width, image.channels))

    vertex_group_assignments = {color: set() for color in unique_colors}

    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            vertex_index = mesh.loops[loop_idx].vertex_index
            uv = uv_layer[loop_idx].uv
            x, y = int(uv.x * (width - 1)), int(uv.y * (height - 1))
            pixel_value = np.mean(pixels[y, x]) if image.channels > 1 else pixels[y, x, 0]
            closest_color = min(unique_colors, key=lambda c: abs(c - pixel_value))
            vertex_group_assignments[closest_color].add(vertex_index)

    groups_created = 0
    for color in sorted(vertex_group_assignments.keys()):
        vertex_indices = vertex_group_assignments[color]
        if len(vertex_indices) >= min_group_size:
            group_name = f"{base_group_name}.{groups_created+1:02d}"
            group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
            for vertex_index in vertex_indices:
                weight = 1.0 - abs(color - pixel_value)
                if weight >= threshold:
                    group.add([vertex_index], weight, 'REPLACE')
            groups_created += 1

    print(f"Created {groups_created} vertex groups")
    return True

def assign_weights_from_texture(obj, image, group_name, normalize):
    mesh = obj.data
    if not mesh.uv_layers.active:
        raise ValueError("No active UV map found. Please ensure the object has an active UV map.")

    uv_layer = mesh.uv_layers.active.data
    width, height = image.size
    pixels = np.array(image.pixels[:]).reshape((height, width, image.channels))

    group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)

    weights = []
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            vertex_index = mesh.loops[loop_idx].vertex_index
            uv = uv_layer[loop_idx].uv
            x, y = int(uv.x * (width - 1)), int(uv.y * (height - 1))
            pixel_value = np.mean(pixels[y, x]) if image.channels > 1 else pixels[y, x, 0]
            weights.append((vertex_index, pixel_value))

    if normalize:
        min_weight = min(w for _, w in weights)
        max_weight = max(w for _, w in weights)
        weight_range = max_weight - min_weight
        if weight_range > 0:
            weights = [(idx, (w - min_weight) / weight_range) for idx, w in weights]
        else:
            weights = [(idx, 1.0) for idx, w in weights]

    for vertex_index, weight in weights:
        group.add([vertex_index], weight, 'REPLACE')

    print(f"Created vertex group '{group_name}' with weights from texture")
    return True

def register():
    bpy.utils.register_class(VGBT_OT_create_groups)
    bpy.utils.register_class(VGBT_PT_main_panel)

def unregister():
    bpy.utils.unregister_class(VGBT_PT_main_panel)
    bpy.utils.unregister_class(VGBT_OT_create_groups)

if __name__ == "__main__":
    register()
