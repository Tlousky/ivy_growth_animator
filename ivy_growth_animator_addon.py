# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
#
#
#  Author            : Tamir Lousky (tlousky@gmail.com)
#
#  Homepage(Wiki)    : http://biological3d.wordpress.com/
#
#  Start of project              : 2013-01-21 by Tamir Lousky
#  Last modified                 : 2013-02-01
#
#  Acknowledgements 
#  ================
#
#  Blender: Patrick Boelens (tuts on CG Cookie!), batFINGER (explained how to
#           keyframe shapekeys on BA forum!), CoDEmanX (useful bmesh API info
#           on BA forums!), frigge (explained how to create an object selection
#           box on BA forums!), anyone who took the time to contribute to the
#           API docs!

bl_info = {    
    "name"        : "Ivy Growth Animator",
    "author"      : "Tamir Lousky",
    "version"     : (1, 0, 0),
    "blender"     : (2, 65, 0),
    "category"    : "Object",
    "location"    : "3D View >> Tools",
    "wiki_url"    : "http://bioblog3d.wordpress.com/2013/02/06/iga-is-ready/",
    "download_url": "https://github.com/Tlousky/ivy_growth_animator",
    "description" : "Animate the growth of Ivy and Trees."
    }

import bpy, bmesh, mathutils, random

class IvyGrowthAnimator( bpy.types.Panel ):
    bl_idname      = "IvyGrowthAnimatorPanel"
    bl_label       = "Ivy Growth Animator"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_context     = 'objectmode'

    # Draw panel UI elements #
    def draw( self, context):                
        layout = self.layout
        obj = context.object

        BranchesAnimProperties = context.scene.BranchesAnimProperties  
        LeavesAnimProperties   = context.scene.LeavesAnimProperties

        col = layout.column()
        col.prop_search(          
            obj, "BranchObject",      # Pick BranchObject out of 
            context.scene, "objects"  # the list of objects in the scene
            )
        col.prop_search(          
            obj, "LeavesObject",      # Pick LeavesObject out of 
            context.scene, "objects"  # the list of objects in the scene
            )
        
        box = layout.box()
        col = box.operator( "object.animate_branches" )
        col = box.operator( "object.animate_leaves"   )
        
        col = layout.column()
        col.label(text="Animation Paremeters")
        
        box = layout.box()
        box.label(text="Branches animation parameters"      )
        box.prop( BranchesAnimProperties, "frame_start"     )
        box.prop( BranchesAnimProperties, "faces_per_frame" )
        box.prop( BranchesAnimProperties, "delay_branches"  )
        box.prop( BranchesAnimProperties, "initial_delay"   )
        
        box = layout.box()
        box.label(text="Leaves animation parameters"         )
        box.prop( LeavesAnimProperties, "delay_after_branch" )
        box.prop( LeavesAnimProperties, "max_growth_length"  )
        box.prop( LeavesAnimProperties, "min_growth_length"  )

# Button for animating the branches of the plant
class AnimateBranches( bpy.types.Operator ):
    """Animate the BranchObject selected above"""
    bl_idname      = "object.animate_branches"
    bl_label       = "Animate Branches"
    bl_description = "Animate the BranchObject selected above"
    bl_options     = { 'REGISTER', 'UNDO' }

    def execute(self, context):
        branch_props = context.scene.BranchesAnimProperties

        object_name = branch_props.prepare_ivy_object( branch_props.modifier_name )

        if object_name == "":
            print( "No object selected, exiting!" )
            return

        ivy_objects = branch_props.find_ivy_branches( object_name )
        
        ( biggest_obj, most_faces, base_build_length ) = branch_props.find_biggest_branch( 
                ivy_objects, branch_props.faces_per_frame )

        branch_props.set_build_timing(
            ivy_objects,
            branch_props.frame_start,
            branch_props.delay_branches,
            branch_props.delay_branches,
            most_faces,
            base_build_length)

        return {'FINISHED'}

# Button for animating the branches of the plant
class AnimateLeaves( bpy.types.Operator ):
    """Animate the LeavesObject selected above"""
    bl_idname = "object.animate_leaves"
    bl_label  = "Animate Leaves"
    bl_description = "Animate the LeavesObject selected above"
    bl_options = { 'REGISTER', 'UNDO' }

    def execute(self, context):
        leaves_props = context.scene.LeavesAnimProperties
        leaves       = context.object.LeavesObject
        branches     = bpy.context.object.BranchObject

        if branches == "":
            print( "No object selected, exiting!" )
            return

        ivy_objects  = bpy.context.scene.BranchesAnimProperties.find_ivy_branches( 
            branches )

        leaves_props.animate_leaves( leaves, ivy_objects )
        
        return {'FINISHED'}

class BranchesAnimProperties( bpy.types.PropertyGroup ):

    def prepare_ivy_object( self, modifier_name ):
        """ function name:  prepare_ivy_object
            description:    converts the active ivy object (which must be selected) form a curve into a mesh,
                            places the 3D cursor at the first point of the ivy curve
                            sorts all faces according to the distance from the 3D cursor (placed on the first point)
                            adds a standard build modifier to this object
                            and eventually splits according to loose parts
        """

        ivy_obj_name = bpy.context.object.BranchObject  # Get selected object's name
        
        if ivy_obj_name == "":
            return ""

        obj = bpy.data.objects[ivy_obj_name]
        
        print( "Got name: ", ivy_obj_name )
        
        # Find the first point of the ivy curve, and place the 3D curser there
        first_curve_point = obj.data.splines[0].points[0].co  # Coords of first curve point
        
        # Set the 3D cursor position to the first curve point
        # I'm creating a new vector since the point natively comes with 
        # 4 arguments instead of just xyz, and this produces an error 
        # when trying to set the cursor there
        bpy.context.scene.cursor_location = mathutils.Vector( [ 
            first_curve_point.x, 
            first_curve_point.y, 
            first_curve_point.z ] )
        
        # Select object
        obj.select = True
        bpy.context.scene.objects.active = obj

        bpy.ops.object.convert(target='MESH')       # object to mesh
        bpy.ops.object.mode_set(mode='EDIT' )       # Go to edit mode
        bpy.ops.mesh.sort_elements(                 # Sort faces by 3D cursor distance
            type='CURSOR_DISTANCE',
            elements={'FACE'})       
        obj.modifiers.new( modifier_name, 'BUILD' ) # Add a Build modifier
        bpy.ops.mesh.select_mode(                   # Goto face selection mode
            use_extend=False,
            use_expand=False,
            type='FACE')   
        bpy.ops.mesh.select_all()                   # Select all faces
        bpy.ops.mesh.separate(type='LOOSE')         # split by loose parts
        bpy.ops.object.mode_set(mode='OBJECT')              # Go to object mode
        
        return ivy_obj_name


    def find_ivy_branches( self, base_name ):
        """ function name:  find_ivy_branches
            description:    browses all objects and filters out those who have the base_name in their names
            return value:   an array (ivy_objects) which contains a list of dictionaries with the name and facecount of each ivy object
        """
        
        ivy_objects = []
        for current_obj in bpy.data.objects:                 # browse all objects and filter out ivy branches
            if base_name in current_obj.name:                # if the object name contains the base_name
                current_obj.data.update(calc_tessface=True)  # calculate face data so that...
                face_count = len(current_obj.data.tessfaces) # we can obtain the total number of faces
                ivy_objects.append( {                        # add ivy object to list:
                    "name" : current_obj.name,               #   include name 
                    "facecount" : face_count } )             #   and face count

        return ivy_objects

    def find_biggest_branch(self, ivy_objects, faces_per_frame):
        biggest_obj = ""
        most_faces  = 0

        # Find the biggest object (highest face count)
        for obj in ivy_objects:
            if obj["facecount"] > most_faces:   # if this object's facecount is larger than the previous highscore,
                most_faces  = obj["facecount"]  # then make this facecount one the new max
                biggest_obj = obj["name"]       # and update the biggest object's name

        # set base build animation length according to the biggest object's size
        base_build_length = int( most_faces / faces_per_frame )
        return biggest_obj, most_faces, base_build_length

    def set_build_timing( self, ivy_objects, build_start_frame, build_interval, wait_between_branches, most_faces, base_build_length):    
        count = 0

        modifier_name = bpy.context.scene.BranchesAnimProperties.modifier_name

        # set animation length and start frames to all objects in list
        for obj in ivy_objects:
            name = obj["name"]
            current_object = bpy.data.objects[name]
        
            # set the start frame of each object's build anim. 
            # by the order of names (which corresponds to order of creation)
            if count != 0: # Set build start for all the branches after the first one:
                bpy.data.objects[name].modifiers[modifier_name].frame_start = int( 
                build_start_frame + build_interval + count * wait_between_branches )
            else:   # Set when the first branch starts to build
                bpy.data.objects[name].modifiers[modifier_name].frame_start = int( build_start_frame )
            
            # Set build length in proportion to face count
            ratio = obj["facecount"] / most_faces
            bpy.data.objects[name].modifiers[modifier_name].frame_duration = int( ratio * base_build_length )

            count += 1

    frame_start = bpy.props.IntProperty(  # When to start animating
        name="frame_start",               # the branches
        description="Growth animation's start point (frame)",
        default=1
        )
    faces_per_frame = bpy.props.IntProperty( # Controls the speed of the
        name="faces_per_frame",              # animation
        description="Speed of the animation (higher values = faster)",
        default=4
        )
    delay_branches = bpy.props.IntProperty( # Frames to wait between
        name="delay_branches",              # branches
        description="Number of frames to wait between branch builds",
        default=4
        )
    initial_delay = bpy.props.IntProperty( # Frames to wait between
        name="initial_delay",              # before starting with branch no. 2
        description="Number of frames to wait before animating 2nd branch",
        default=15
        )
    modifier_name = bpy.props.StringProperty(
        name="modifier_name", default="GROW" )

class LeavesAnimProperties( bpy.types.PropertyGroup ):

    def find_nearest_face_on_mesh( self, mesh_obj, coordinates):
        """ function name:  find_nearest_face_on_mesh
            parameters:     mesh_obj    - The object whose faces we want to access
                            coordinates - the coordinates of the current leaf
            description:    Iterates over all the faces in a mesh and find the one which is closest
                            to the coordinates provided.
            return value:   The smallest distance between any of the mesh's faces and the coordinates
        """

        mesh_obj.data.update( calc_tessface=True )
        distances = []
        for face in mesh_obj.data.tessfaces:
            pt1 = face.center * mesh_obj.matrix_world # convert to global coordinates
            pt2 = coordinates
            distance = abs(pt1.x - pt2.x) + abs(pt1.y - pt2.y) + abs(pt1.z - pt2.z)
            distances.append(distance)
            
        distances.sort()
        
        return distances[0]  # return the first value which is the smallest after sorting
        
    def find_nearest_branch( self, ivy_objects, glob_co ):
        """ function name:  find_nearest_branch
            parameters:     ivy_objects [List] - Array of ivy branches
                            global_co [Vector] - the coordinates of the object we want to
                                                 match with the nearest branch
            description:    Finds the nearest branch to the coordinates it gets as a parameter
                            Iterates over branches and returns the closest one
            return value:   The closest ivy branch (mesh object)
        """
        # First we'll calculate the first ivy branch's distance from the current leaf.
        # The we'll browse all branches and find if any other branch is closer to our leaf.

        closest_object   = ivy_objects[0]   # First branch is the initial closest object
        branch_obj       = bpy.data.objects[closest_object["name"]]
        minimum_distance = self.find_nearest_face_on_mesh( branch_obj, glob_co)

        for branch in ivy_objects:
            branch_obj = bpy.data.objects[branch["name"]]
            distance = self.find_nearest_face_on_mesh( branch_obj, glob_co)
            
            if distance < minimum_distance:
                minimum_distance = distance
                closest_object   = branch
        
        return closest_object

    def create_shapekey( self, leaves, leaf_idx, start, duration ):
        """ function name:  create_shapekey
            parameters:     leaves   [Mesh obj]   - the leaves mesh object
                            leaf_idx [Face Index] - Index of the leaf to be transformed and shape keyed
                            start    [Int]        - The start frame for the closest branch's build modifier
                            duration [Int]        - The duration of the closest branch's build modifier
            description:    Creates a shape key for the current leaf (face on leaves mesh object),
                            which will enable to animate the progressive growth of this leaf on its branch
        """    
        
        bpy.ops.object.shape_key_add(from_mix=False) # Create a shapekey for this leaf
        latest_shape_key_index = len(bpy.context.object.data.shape_keys.key_blocks) - 1
        current_shape_key      = bpy.context.object.data.shape_keys.key_blocks[latest_shape_key_index]
        bpy.context.object.active_shape_key_index = latest_shape_key_index  # Activate current shape key
        
        bpy.ops.object.mode_set(mode = 'EDIT')              # edit mode to deselect all
        bpy.ops.mesh.select_mode(                           # Go to vertex selection mode
            use_extend=False, 
            use_expand=False, 
            type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')          # Deselect all verts
        bpy.ops.object.mode_set(mode = 'OBJECT')            # Go back to object mode
        bpy.context.object.data.update(calc_tessface=True)  # Calculate the face data again
        
        # select face vertices
        idxmin = 0
        length = len(bpy.context.object.data.tessfaces[leaf_idx].vertices)
        for i in range(idxmin, length):
            vert_index = bpy.context.object.data.tessfaces[leaf_idx].vertices[i]
            bpy.context.object.data.vertices[vert_index].select = True

        bpy.ops.object.mode_set(mode = 'EDIT')    # edit mode to edit face
        bpy.ops.mesh.select_mode(                 # Go to face selection mode
            use_extend=False, 
            use_expand=False, 
            type='FACE')
        bpy.ops.transform.resize(value=(0,0,0))   # resize face to 0 (invisible)
        bpy.ops.object.mode_set(mode = 'OBJECT')  # return to object mode

        build_start_frame = bpy.context.scene.BranchesAnimProperties.frame_start

        # Create the first keyframe where the value of the shapekey is 1 to make the leaf invisible at the beginning
        bpy.context.scene.frame_set(build_start_frame) # Select frame for keyframe
        current_shape_key.value = 1                          # Set shapekey value
        current_shape_key.keyframe_insert('value')           # Insert keyframe for shapekey val
        
        # Create the keyframe where the growth begins (leaf still invisible)
        start_frame = start + duration + random.randint(0, self.delay_after_branch)
        bpy.context.scene.frame_set(start_frame) # Select frame for keyframe
        current_shape_key.value = 1                    # Set shapekey value
        current_shape_key.keyframe_insert('value')     # Insert keyframe for shapekey val    
        
        # Create the keyframe where the growth ends (leaf at full size)
        end_frame = start_frame + random.randint(self.min_growth_length, self.max_growth_length)
        bpy.context.scene.frame_set(end_frame)   # Select frame for keyframe
        current_shape_key.value = 0                    # Set shapekey value
        current_shape_key.keyframe_insert('value')     # Insert keyframe for shapekey val    

    def animate_leaves( self, leaves_object_name, ivy_objects ):
        """ function name:  animate_leaves
            parameters:     leaves_object_name [string]
                            ivy_objects        [List of Mesh Objects]
            description:    Master function for the leaves' animations. Iterates over all leaves,
                            calculates what branch is the closest to each, and uses that information
                            to create and animate shapekeys where this leaf grows gradually
        """
        leaves = bpy.data.objects[leaves_object_name]
        leaves.select = True                       # Select leaves object
        bpy.context.scene.objects.active = leaves  # Make leaves the active object in the scene
        
        bpy.ops.object.shape_key_add(from_mix=False) # Create the first, base shapekey
        leaves.data.update(calc_tessface=True)       # Calculate the face data
        
        leaf_indices = []
        for leaf in leaves.data.tessfaces:
            leaf_indices.append(leaf.index)

        worldmatrix = leaves.matrix_world
        branch_props = bpy.context.scene.BranchesAnimProperties

        modifier_name = branch_props.modifier_name
        
        for index in leaf_indices:
            leaves.data.update(calc_tessface=True)                                   # Calculate the face data
            leaf_center_pos_glob = leaves.data.tessfaces[index].center * worldmatrix # Get the global coordinates of this leaf's center
            branch     = self.find_nearest_branch(ivy_objects, leaf_center_pos_glob)      # Find closest branch to this leaf
            branch_obj = bpy.data.objects[branch["name"]]
            start      = branch_obj.modifiers[modifier_name].frame_start             # Get start frame for this branch's build modifier
            duration   = branch_obj.modifiers[modifier_name].frame_duration          # And the modifier's duration
            self.create_shapekey( leaves, index, start, duration)                         # Create a shapekey for this leaf

    # Leaf Animation Properties
    delay_after_branch = bpy.props.IntProperty(  # No. of frames to wait after
        name="delay_after_branch",               # closest branch finished
        description="Frames to wait before animating leaf after closest branch finished animating",
        default=10
        )
    max_growth_length = bpy.props.IntProperty(  # Maximum growth animation length
        name="max_growth_length", 
        description="Maximum length for the growth animation of a leaf",
        default=25
        )
    min_growth_length = bpy.props.IntProperty(  # Minimum growth animation length
        name="min_growth_length", 
        description="Minimum length for the growth animation of a leaf",
        default=10
        )

def register():
    bpy.utils.register_module(__name__)
    # Create poperties for branch and leaf object selection boxes (in the panel)
    bpy.types.Object.BranchObject = bpy.props.StringProperty()
    bpy.types.Object.LeavesObject = bpy.props.StringProperty()
    bpy.types.Scene.BranchesAnimProperties = bpy.props.PointerProperty(type=BranchesAnimProperties)
    bpy.types.Scene.LeavesAnimProperties   = bpy.props.PointerProperty(type=LeavesAnimProperties  )
    
def unregister():
    bpy.utils.unregister_module(__name__)