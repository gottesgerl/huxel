import hou
import mouseevents

def create_objmerge(display=1, connect=0, select=1, good_position=0, hide_badges=1, **kwargs):
    # creates an object merge node which points to the node under the cursor 
    node = hou.node(kwargs["path"])
    parent = node.parent()    
    position_offset = hou.Vector2(0,-1)
    newpos = node.position()+position_offset    
    if 'OUT' in node.name():   newname = node.name().replace('OUT', 'IN')
    else:                       newname = 'IN_'+node.name()
    newnode = parent.createNode("object_merge", node_name=newname, force_valid_node_name=True)
    newnode.parm("objpath1").set(node.path())
    if select: newnode.setSelected(True, True)
    if display and node.isDisplayFlagSet(): newnode.setDisplayFlag(1)
    if display and node.isRenderFlagSet():  newnode.setRenderFlag(1)
    if hide_badges:                         newnode.setDisplayDescriptiveNameFlag(False)
    if good_position:                       newnode.moveToGoodPosition(move_inputs = False, move_outputs = False, move_unconnected = False)        
    else:                                   newnode.setPosition(newpos)
    return newnode
    
    
def create_objmerge_in_new_geo(display=1, select=1, good_position=0, hide_badges=1, **kwargs):
    # creates an object merge node in an new geometry node points to the node under the cursor and jumps there
    node = hou.node(kwargs["path"])
    editor = hou.ui.curDesktop().findPaneTab(kwargs["editor"])    
    parent = node.parent()    
    position_offset = hou.Vector2(0,-1)
    newpos = node.position()+position_offset    
    if 'OUT' in node.name():    newname = node.name().replace('OUT', 'IN')
    else:                       newname = 'IN_'+node.name()
    #geo node
    geoname = newname.replace('IN', '')
    obj_context = hou.node("/obj")
    #obj merge
    newgeo = obj_context.createNode("geo", node_name=geoname, force_valid_node_name=True)
    newgeo.moveToGoodPosition()       
    newnode = newgeo.createNode("object_merge", node_name=newname, force_valid_node_name=True)
    newnode.parm("objpath1").set(node.path())
    if hide_badges:                         newnode.setDisplayDescriptiveNameFlag(False)
    #jump
    mouseevents.centerNode(editor, newnode)
    return newnode
    
def eigenvector_boundingbox(**kwargs):
    # creates an object merge node which points to the node under the cursor
    node = hou.node(kwargs["path"])
    editor = hou.ui.curDesktop().findPaneTab(kwargs["editor"])    
    parent = node.parent()    
    position_offset = hou.Vector2(0,-1)
    newpos = node.position()+position_offset  
    pass    
    