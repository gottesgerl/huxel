from __future__ import print_function
from __future__ import division
from platform import node
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
from builtins import next
from past.utils import old_div
import hou
import math
import time
import traceback
import pdgd
import string
import re 

import nodegraphbase as base
import nodegraphpopupmenus as popupmenus
import nodegraphautoscroll as autoscroll
import nodegraphflags as flags
import nodegraphgestures as gestures
import nodegraphhotkeys as hotkeys
import nodegraphconnect as connect
import nodegraphdisplay as display
import nodegraphfastfind as fastfind
import nodegraphpalettes as palettes
import nodegraphprefs as prefs
import nodegraphsnap as snap
import nodegraphstates as states
import nodegraphui as ui
import nodegraphutils as utils
import nodegraphview as view
import nodegraphhooks as hooks
import nodegraphtopui as topui

import importlib
from canvaseventtypes import *

# to avoid cycle dependencies
path = importlib.util.find_spec('nodegraph') 
ng = path.loader.load_module()


#-------------------------------------------VARIABLES NEEDED FOR DEFAULT BEHAVIOUR -----------------------------------   

theFlagDecorators =             ( 'flag', 'flagindicator' )
theFlagTogglers =               ( 'flag', 'flagindicator', 'footerflag' )
theNodeSelectors =              ( 'node', 'connectorarea', 'preview', 'footer' )
theNodeDraggers =               ( 'node', 'connectorarea', 'inputgroup','flagindicator', 'preview', 'footer' )
theNodeInfoPoppers =            ( 'node', 'connectorarea','flagindicator', 'preview', 'footer', 'input', 'output' )
theInfoTogglers =               ( 'info', 'indirectinputinfo' )
theFlyoutExpansions =           ( 'nodeexpanded', 'indirectinputexpanded', 'dotexpanded' )
thePaletteBorders =             ( 'colorpaletteborder', 'shapepaletteborder' )
thePaletteBackgrounds =         ( 'colorpalette', 'shapepalette' )
theSkipDecorators =             ( 'input', 'inputgroup', 'connectorarea', 'output', 'multiinput', 'name','preview', 'previewplane', 'footer', 'footerflag','taskgraphworkitem')
theFlyoutParts =                ( 'nodeexpanded', 'info','flag','indirectinputexpanded', 'indirectinputinfo','dotexpanded', 'dotinput', 'dotoutput')
theBackgroundImageElements =    ( 'backgroundimage', 'backgroundimageborder', 'backgroundimagedelete', 'backgroundimagelink', 'backgroundimagebrightness')
theBackgroundImageDraggables =  ( 'backgroundimage', 'backgroundimageborder', 'backgroundimagelink', 'backgroundimagebrightness')

#------------------------------------------- SETTINGS -----------------------------------    

radius_around_nodes = 2.0



def getVisibleNodes(uievent, max_distance=-1):
    #collects a list of all nodes visible an this editor 
    # and sorts them by their distance to the mouse position (closest first)
    editor = uievent.editor
    pane_size = editor.size()
    path = editor.pwd().path()
    mousepos =  uievent.mousepos
    mousepos_nwspace = editor.posFromScreen(mousepos)
    pos1 = hou.Vector2(0,0)
    pos2 = hou.Vector2(pane_size[0], pane_size[1])
    allItems = editor.networkItemsInBox(pos1, pos2, for_drop="False", for_select="False")
    allNodes = [ i[0] for i in allItems if i[1]=='node']
    #distance method no1:    allDistances = { i:i.position().distanceTo(mousepos_nwspace) for i in allNodes }
    #distance method no2:    allDistances = { i:editor.itemRect(i).center().distanceTo(mousepos_nwspace) for i in allNodes }
    #distance method no3:   which takes the nodes shape boundaries into account
    allDistances = { i:editor.itemRect(i).closestPoint(mousepos_nwspace).distanceTo(mousepos_nwspace) for i in allNodes }
    allPositions = { i:i.position() for i in allNodes }
    nodesByDistance = {k: v for k, v in sorted(allDistances.items(), key=lambda item: item[1]) if v < max_distance}
    nodes = list(nodesByDistance.keys())
    return nodes

def setDisplayFlags(editor, node):
    # set display flag to closest node
    # move the renderflag with it if both were on the same node
    theDisplayFlagContexts = ("Sop", "Cop", "Lop", "Dop", "Chop")
    parent = editor.pwd()
    context = parent.childTypeCategory().name()
    if context == "Object":
        node.setDisplayFlag(abs(node.isDisplayFlagSet()-1))
    elif context in theDisplayFlagContexts:
        cur_display = parent.displayNode()
        if cur_display is not None and hasattr(cur_display, "isRenderFlagSet") \
                and cur_display.isRenderFlagSet() and hasattr(node, "setRenderFlag"):
            node.setRenderFlag(True)
        node.setDisplayFlag(True)

def bypassToggle(editor, node):
    # toggle bypass on/off
    # obj-level: toggle selectable
    theBypassContexts =             ( 'Sop', 'Cop', 'Lop', 'Dop', 'Chop', 'Vop', 'Top' )
    parent = editor.pwd()
    context = parent.childTypeCategory().name()
    if context in theBypassContexts:
        node.bypass(not node.isBypassed())
    elif context == "Object":
        node.setSelectableInViewport(not node.isSelectableInViewport())
        
def toggleBatches(node):
    cur_state = node.isDisplayDescriptiveNameFlagSet()
    node.setDisplayDescriptiveNameFlag(not cur_state)

def storeViewCycle(editor):
    # stores the selected nodes
    # to be view cycled later
    commentsEnabled = True
    letters = string.ascii_uppercase
    parent = editor.pwd()
    selected = parent.selectedChildren()
    hou.ui.setStatusMessage("Selection Stored. %s nodes." %len(selected), hou.severityType.ImportantMessage)
    #clear comments on former nodes
    if commentsEnabled:
        for child in parent.children():
            try:            
                c = re.sub(r"VIEW [ABC](\n)", "", child.comment())
                child.setComment(c)
                if not c: c.setGenericFlag(hou.nodeFlag.DisplayComment, False)
            except:
                pass 
    parent.setCachedUserData("view_toggle", selected)        
    #create comments
    if commentsEnabled:
        for i in range(len(selected)):
            s = selected[i]
            c = "{0}\n{1}".format("VIEW %s" %letters[i%len(letters)], s.comment())
            s.setComment(c)
            s.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    
    
def viewCycle(editor):
    # cycles the display flag
    # through the stored nodes
    parent = editor.pwd()
    cycle_nodes = parent.cachedUserData("view_toggle")
    displayNode = parent.displayNode()    
    if not cycle_nodes:
        msg = "No Stored Selection. Please select some nodes and Ctrl+Shift+Atl+Doubleclick."
        hou.ui.setStatusMessage(msg, hou.severityType.Warning)
    elif len(cycle_nodes)<2:
        msg = "Only one node stored. Please select 2 nodes and store them with Ctrl+Shift+Atl+Doubleclick."
        hou.ui.setStatusMessage(msg, hou.severityType.ImportantMessage)
    else:
        if displayNode not in cycle_nodes:
            setDisplayFlags(editor, cycle_nodes[0])
        else:                
            for n in range(len(cycle_nodes)):
                if cycle_nodes[n]==displayNode:
                    setDisplayFlags(editor, cycle_nodes[(n+1)%len(cycle_nodes)])

theTemplateContexts =           ( 'Sop', 'Cop' )
theShadedTemplateContexts =     ( 'Sop', 'Cop', )

def templateToggle(editor, node):
    # toggle template flag
    # VOP: toggle debug flag
    # obj-level: remove from selection
    parent = editor.pwd()
    context = parent.childTypeCategory().name()
    if context in theTemplateContexts:
        if context in theShadedTemplateContexts and node.isSelectableTemplateFlagSet():
            node.setSelectableTemplateFlag(False)
            node.setTemplateFlag(True)
        else:
            node.setTemplateFlag(not node.isTemplateFlagSet())          
    elif context == "Vop":
        node.setDebugFlag(not node.isDebugFlagSet())
    elif context == "Object":
        node.setSelected(False)

def shadedTemplate(editor, node):
    # toggles shaded template flag
    # turns of template flag together with selectable template flag
    parent = editor.pwd()
    context = parent.childTypeCategory().name()
    if context not in theShadedTemplateContexts: return
    value = not node.isSelectableTemplateFlagSet()
    node.setSelectableTemplateFlag(value)
    if not value: node.setTemplateFlag(False)
    
def setSelection(editor, node):
    #selects the closest node
    time.sleep(.1)
    if editor.currentNode() != node:        editor.setCurrentNode(node)
    if not node.isSelected():               node.setSelected(True)
    time.sleep(.1)

    
def centerNode(editor, node):
    # centers the node in the editor
    view.changeNetwork(editor, node.parent())
    n_ctr = editor.itemRect(node).center()
    bounds = editor.visibleBounds()
    move = n_ctr-bounds.center()
    bounds.translate(move)
    editor.setVisibleBounds(bounds)
    
    
#-------------------------------------------NODE specific functions


#---------- SOP Nodes

def handle_SOPobjectMerge(editor, node):
    # OBJECT MERGE 
    # goto input1
    # /// DELETE ME -- path = node.parm("objpath1").evalAsNodePath()
    # /// DELETE ME -- target = hou.node(path)
    target = node.parm("objpath1").evalAsNode()
    if target:
        centerNode(editor, target)
        setSelection(editor, target)

def handle_SOPnull(editor, node):
    # NULL 
    # go to dependent nodes
    targets = node.dependents()
    if targets:
        target = targets[0]
        centerNode(editor, target)
        setSelection(editor, target)

def handle_SOPmerge(editor, node):
    conns = node.inputConnections()
    if len(conns) < 2:        return
    wired = []
    for c in conns:
        src  = c.inputNode()
        item = c.inputItem()
        if src is None or item is None:  return
        wired.append((c.inputIndex(), src, item, c.outputIndex()))
    current = [w[1:] for w in sorted(wired, key=lambda w: w[0])]
    target  = [w[1:] for w in sorted(wired, key=lambda w: (w[1].position()[0], -w[1].position()[1]))]
    # do nothing if order is ok
    if current == target: return
    with hou.undos.group("Reorder Merge Inputs"):
        for i, (_src, item, out_idx) in enumerate(target):
            node.setInput(i, item, out_idx)
    
def handle_SOPmaterial(editor, node):
    # Material 
    # go to dependent nodes    
    try:
        #target = node.parm("shop_materialpath1").evalAsNode().dependents()[1]
        target = node.parm("shop_materialpath1").evalAsNode()
        if target: target.setCachedUserData("huxel_mat_origin", node.path())        
    except: 
        target = None
    if target:
        if      target.type().name() == "redshift_vopnet":    view.changeNetwork(editor, target)
        elif    target.type().name() == "subnet":             view.changeNetwork(editor, target)
        else:
            centerNode(editor, target)
            setSelection(editor, target)

def handle_SOPswitch(uievent, editor, node):
    # SWITCH 
    # switch inputs up and down
    input = node.parm("input").eval()
    if node.inputs(): 
        new_input = (input+1)%(len(node.inputs()))
        # SHIFT --> move downwards
        if uievent.modifierstate.shift:
            new_input = (input-1)%(len(node.inputs()))
        node.parm("input").set(new_input)

# -------------------------------------------VISUALIZER TOGGLE

# fixed visualizer presets for special attributes
NEW_ATTR_VIS_PRESETS = {
    "Cd":    {"type": "vis_color"},
    "noise": {"type": "vis_color"},
    "speed": {"type": "vis_marker", "style": "vector", "unitlength": 0.5, "arrowheads": 1},
    "v":     {"type": "vis_marker", "style": "vector"},
    "N":     {"type": "vis_marker", "style": "vector", "normalize": 1},
    "mask":  {"type": "vis_marker", "style": "text"},
    "orient": {"type": "vis_marker", "style": "axes", "lengthscale": 0.1},
}

def _vis_spec(geo, attrib):
    try: attr = geo.findPointAttrib(attrib)
    except hou.Error:  attr = None
    vtype, parms = "vis_marker", {"style": "text"}          # fallback: value as text
    if attr is not None:
        qual = ""
        try: qual = (attr.qualifier() or "").lower()            # 'color','vector','normal','point',''
        except (AttributeError, hou.Error): pass
        is_float3 = (attr.dataType() == hou.attribData.Float and attr.size() == 3)
        if qual == "color" or attrib == "Cd":
            vtype, parms = "vis_color", {}                  # surface tint by color
        elif qual in ("vector", "normal", "point") or is_float3:
            vtype, parms = "vis_marker", {"style": "vector"}  # arrows
    # --- name preset overrides on top ---
    preset = dict(NEW_ATTR_VIS_PRESETS.get(attrib, {}))
    vtype = preset.pop("type", vtype)
    parms.update(preset)
    return vtype, parms


def _geo_attribs(geo):
    # collect all attributes
    keys = set()
    if geo is None:
        return keys
    for cls, attribs in (("point",  geo.pointAttribs()), 
                         ("vertex", geo.vertexAttribs()),
                         ("prim",   geo.primAttribs()),
                         ("detail", geo.globalAttribs())):
        for a in attribs:
            keys.add((cls, a.name()))
    return keys

def _marker_style(geo, attrib):
    # find best visualization style
    style = "marker"
    try:
        a = geo.findPointAttrib(attrib)
    except hou.Error:
        a = None
    if a is not None:
        if attrib == "Cd":      style = "color"
        elif a.size() == 3:     style = "vector"
    return style

def handle_newAttribVis(editor, node):
    # visualize toggle
    VIS_TAG = "huxel_newattr__"
    cat = hou.viewportVisualizerCategory.Node
    if not isinstance(node, hou.SopNode):   return
    # Toggle off
    displayed = node.isDisplayFlagSet()
    existing = [v for v in hou.viewportVisualizers.visualizers(cat, node=node) if v.name().startswith(VIS_TAG)]
    if existing and displayed:
        for v in existing: v.destroy()
        return
    # Toggle on (+kill old one)
    for v in existing: v.destroy()
    try:   cur = _geo_attribs(node.geometry())
    except hou.Error:   return 
    incoming = set()
    for input in node.inputs(): incoming |= _geo_attribs(input.geometry())
    new_keys = sorted(cur - incoming)
    new_points = [name for cls, name in new_keys if cls == "point"]
    other      = [(cls, name) for cls, name in new_keys if cls != "point"]
    if not new_points: return
    geo = node.geometry()
    vtype = hou.viewportVisualizers.type("vis_marker")
    with hou.undos.group("Visualize New Attributes"):
        for name in new_points:
            vtype, parms = _vis_spec(geo, name)
            vis = hou.viewportVisualizers.createVisualizer(
                hou.viewportVisualizers.type(vtype), cat, node)
            vis.setName(VIS_TAG + name)
            vis.setLabel("new: " + name)
            vis.setParm("attrib", name)
            for pname, pval in parms.items():
                try: vis.setParm(pname, pval)
                except hou.Error:   pass
            vis.setIsActive(True)
    try: setDisplayFlags(editor, node)
    except (NameError, hou.Error):
        try: node.setDisplayFlag(True)
        except hou.Error: pass    

def create_geo_node(uievent, editor, jump=1):
    #create a geo node and jumps into
    newgeo = editor.pwd().createNode("geo")
    pos = editor.posFromScreen(uievent.mousepos)
    newgeo.setPosition(pos)
    if jump: view.changeNetwork(editor, newgeo)
    
def jump_from_material_to_SOP(editor, net=None):
    if net is None: net = editor.pwd()
    origin = net.cachedUserData("huxel_mat_origin")
    target = hou.node(origin) if origin else None
    if not target:
        mat_type = hou.nodeType(hou.sopNodeTypeCategory(), "material")
        mats = [d for d in net.dependents() if d.type() == mat_type]
        if mats: target = mats[0]
    if target:
        centerNode(editor, target)
        setSelection(editor, target)    

def handle_LOPsopImport(editor, node):
    target = node.parm("soppath").evalAsNode()
    if target:
        centerNode(editor, target)
        setSelection(editor, target)




#-------------------------------------------MOUSE WHEEL functions


def wheelDiving(uievent, editor, wheel_direction):
    # Move one level up or dive
    # into the node under pointer
    block_managers = 1
    if wheel_direction == "up": 
        node = editor.pwd().parent()
        #dont jump too far up
        if block_managers and node.name() == "/":   node=None
        #handle dive targets
        else:
            if node:
                while node.isInsideLockedHDA(): node = node.parent().parent()
        view.changeNetwork(editor, node)
    elif wheel_direction == "down": 
        if uievent.located.item != None:
            node = hou.node(uievent.located.item.path())
            view.changeNetwork(editor, node)
    time.sleep(.1)


#----------------------------------------- NODE SHAPE SCALING

SIZE_RE = re.compile(r"_(s|l)(\d+)$")

def _family_base(shape, all_shapes):
    """Canonical (default) base name for any size-variant shape."""
    m = SIZE_RE.search(shape)
    if not m:
        return shape                       # already a base shape
    stem = SIZE_RE.sub("", shape)          # 'circl' (small) or 'circle' (large)
    if m.group(1) == "l":
        return stem                        # large stem is intact
    for cand in all_shapes:                # small stem lost a char -> find owner
        if not SIZE_RE.search(cand) and cand[:-1] == stem:
            return cand
    return stem                            # fallback

def _size_ladder(base, all_shapes):
    """Smallest -> biggest ordered list for a family."""
    small_stem = base[:-1] + "_s"          # 'circl_s'
    large_stem = base + "_l"               # 'circle_l'
    smalls = sorted(s for s in all_shapes
                    if s.startswith(small_stem) and s[len(small_stem):].isdigit())
    larges = sorted(s for s in all_shapes
                    if s.startswith(large_stem) and s[len(large_stem):].isdigit())
    return smalls + [base] + larges        # index order == physical size order

def wheelNodeScaling(uievent, editor, wheel_direction):
    item = uievent.located.item
    if not isinstance(item, hou.Node):     return    # wheel was over a wire / dot / empty - not a node
    node = item
    all_shapes = editor.nodeShapes()
    current = node.userData("nodeshape") or node.type().defaultShape() or "rect"
    ladder = _size_ladder(_family_base(current, all_shapes), all_shapes)
    if current not in ladder:
        return                             # no size variants for this shape
    i = ladder.index(current)
    if wheel_direction == "down":          # down = bigger (toward large)
        i = min(i + 1, len(ladder) - 1)
    elif wheel_direction == "up":          # up = smaller
        i = max(i - 1, 0)
    node.setUserData("nodeshape", ladder[i])

def wheelChangeNodeshape(uievent, editor, wheel_direction):
    # change node shapes
    shape_lib = ["rect", "circle", "null"]
    #all_shapes = editor.nodeShapes()
    if uievent.located.item != None:
        item = uievent.located.item
        if not isinstance(item, hou.Node):     return    # wheel was over a wire / dot / empty - not a node
        node = item
        nodeshape = node.userData("nodeshape")
        index = shape_lib.index(nodeshape) if nodeshape in shape_lib else -1
        if wheel_direction == "down": 
            new_index = (index+1) % len(shape_lib)
        elif wheel_direction == "up":
            new_index = (index-1) % len(shape_lib)
        new_shape = shape_lib[new_index]
        node.setUserData("nodeshape", new_shape)

def wheelChangeNodecolor(uievent, editor, wheel_direction):
    # change node colors
    # the color library is a list of colors that are used to cycle through the node colors
    # its colors are default grey, orange, green, blue, pink, purple, red, black 
    #color_lib = [(0.6, 0.7, 0.77), (1,0.73,0), (0.14,0.67,.56), (.09,.37,.69), (.89, .41, .76), (0.58,.21,.47), (0.8,.02,0.02), (0,0,0)]
    # its colors are default grey, orange, green, blue, pink, red
    color_lib = [(1,0.73,0), (0.14,0.67,.56), (.09,.37,.69), (.89, .41, .76), (0.8,.02,0.02)]
    color_default =  (0.8, 0.8, 0.8)
    if uievent.located.item != None:
        node = hou.node(uievent.located.item.path())
        #nodecolor = node.color()
        nodecolor = tuple(round(c, 2) for c in node.color().rgb())
        index = color_lib.index(nodecolor) if nodecolor in color_lib else -1
        if wheel_direction == "up":         
            new_index = (index+1) % len(color_lib)
            new_color = color_lib[new_index]
        elif wheel_direction == "down":
            # always set default color
            new_color = color_default
            # or go into reverse order
            # new_index = (index-1) % len(color_lib)
        #new_color = color_lib[new_index]
        node.setColor(hou.Color(new_color))




#-------------------------------------------Left Mouse Button Handler -----------------------------------   

  
class LmbMouseHandler(ng.NodeMouseHandler):

    def handleEvent(self, uievent, pending_actions):
        # the main event handler which
        # distributes each mouse event
        # to its respective subroutines
        
        editor = uievent.editor
        parent = editor.pwd()
        if parent: context = parent.childTypeCategory().name()
           
        if isinstance(uievent, MouseEvent):
            if uievent.selected.item is not None:
                #print(uievent.selected.name)
                if uievent.selected.name.startswith('overview'): 
                    return base.OverviewMouseHandler(uievent)
                    
            SHIFT, CTRL, ALT = 0,0,0
            if uievent.modifierstate.shift: SHIFT = 1
            if uievent.modifierstate.ctrl: CTRL = 1
            if uievent.modifierstate.alt: ALT = 1
            
            if isinstance(uievent, MouseEvent) and uievent.eventtype == 'doubleclick':
                #print("clicker-di-click.")
                #-------------------------------------------double clicking an EMPTY AREA
                if uievent.selected.item == None:
                    #different operations use different search radii                    
                    if SHIFT and CTRL and not ALT:     max_distance = 99 
                    elif SHIFT and CTRL and ALT:       max_distance = 99
                    else:                               max_distance = radius_around_nodes
                    
                    nodes = getVisibleNodes(uievent, max_distance)
                    
                    
                    if nodes:
                        closest_node = nodes[0]

                        # SHIFT --> set selection
                        if uievent.modifierstate.shift and not uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                            setSelection(editor, closest_node)
                                              
                        # SHIFT + CTRL --> cycle stored nodes / add to selection
                        elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                            if context == "Sop":        viewCycle(editor)
                            if context == "Object":     closest_node.setSelected(True)
                                                                             
                        # SHIFT + ALT --> toggle batches
                        elif uievent.modifierstate.shift and not uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                            toggleBatches(closest_node)
                            
                        # SHIFT + ALT + CTRL --> store view selection
                        elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                            if context == "Sop":        storeViewCycle(editor)
                            
                        # CTRL ONLY -->  bypass toggle
                        elif uievent.modifierstate.ctrl and not uievent.modifierstate.alt and not uievent.modifierstate.shift:
                            bypassToggle(editor, closest_node)
                        
                        # ALT --> toogle template flag / remove from selection                 
                        elif uievent.modifierstate.alt and not uievent.modifierstate.ctrl and not uievent.modifierstate.shift:
                            templateToggle(editor, closest_node)
                            
                        # ALT + CTRL --> toogle shaded template mode
                        elif uievent.modifierstate.alt and uievent.modifierstate.ctrl and not uievent.modifierstate.shift:
                            shadedTemplate(editor, closest_node)
                                                        
                        # NO MODIFIER --> set display flag      
                        else:
                            setDisplayFlags(editor, closest_node)
                    #-------------------------------------------double clicking in EMPTY SPACE                
                    else:
                        
                        # NO MODIFIERS --> create geo   
                        if not uievent.modifierstate.shift and not uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                            if context == "Object":     create_geo_node(uievent, editor)
                            if context == "Vop":        jump_from_material_to_SOP(editor) 
                              
                 #-------------------------------------------double clicking a NODE
                else:
                    node =  uievent.selected.item
                    if not isinstance(node, hou.Node): pass
                    
                    #------------------------------------------- double clicking over nodes
                    elif not uievent.modifierstate.ctrl and not uievent.modifierstate.shift and not uievent.modifierstate.alt:
                        type = node.type()

                        if type == hou.nodeType(hou.sopNodeTypeCategory(), "object_merge"):                        
                            handle_SOPobjectMerge(editor, node)

                        if type == hou.nodeType(hou.sopNodeTypeCategory(), "null"):
                            handle_SOPnull(editor, node)

                        if type == hou.nodeType(hou.sopNodeTypeCategory(), "merge"):
                            handle_SOPmerge(editor, node)
                            
                        if type == hou.nodeType(hou.sopNodeTypeCategory(), "switch"):
                            handle_SOPswitch(uievent, editor, node)

                        if type == hou.nodeType(hou.sopNodeTypeCategory(), "material"):
                            handle_SOPmaterial(editor, node)

                        #different materials types
                        if type.name() in ("subnetconnector", "redshift_material", "redshift_usd_material"):
                            jump_from_material_to_SOP(editor, net=None)  

                        if type == hou.nodeType(hou.lopNodeTypeCategory(), "sopimport"):
                            handle_LOPsopImport(editor, node)  

                    #-------------------------------------------CTRL + double clicking over node: VISUALIZER TOGGLE
                    elif uievent.modifierstate.ctrl and not uievent.modifierstate.shift and not uievent.modifierstate.alt:
                        handle_newAttribVis(editor, node) 
                        return None
        
        #------------------------------------------- HANDLING OVERLAYS AND SPECIFIC CASES      
                    
            elif uievent.selected.name == 'colorpalettecolor':
                return palettes.ColorPaletteMouseHandler(uievent)
            elif uievent.selected.name == 'shapepaletteshape':
                return palettes.ShapePaletteMouseHandler(uievent)
            elif uievent.selected.name in ('taskgraphworkitem', 'taskgraphcollapseditem'):
                return ng.WorkItemMouseHandler(uievent)
            elif uievent.selected.name == 'taskgraphpage':
                return ng.TaskGraphPageHandler(uievent)
            elif uievent.selected.name == 'taskgraphopentable':
                return ng.TaskGraphSeeMoreHandler(uievent)
            elif uievent.selected.name in thePaletteBackgrounds:
                return palettes.PaletteBackgroundMouseHandler(uievent)
            elif uievent.selected.name in thePaletteBorders:
                return palettes.PaletteBorderMouseHandler(uievent)
            elif uievent.selected.name in theBackgroundImageElements:
                return ng.BackgroundImageMouseHandler(uievent)    
            elif isinstance(uievent.selected.item, hou.NetworkBox):
                return ng.NetworkBoxMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.StickyNote):
                return ng.StickyNoteMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.SubnetIndirectInput):
                return ng.IndirectInputMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NetworkDot):
                return ng.NetworkDotMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NodeConnection):
                #store the current uievent before it gets consumed 
                last_uievent = uievent  
                return NodeConnectionMouseHandler_huxel(uievent, last_uievent)
            elif isinstance(uievent.selected.item, NodeDependency):
                return ng.NodeDependencyMouseHandler(uievent)        
            '''
            elif uievent.selected.item is None:
                return ng.BackgroundMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.Node):
                handler, handled = ng.createNodeTypeEventHandler(uievent, pending_actions)
                if handled:
                    return handler
                return ng.NodeMouseHandler(uievent)
            '''
        #------------------------------------------- DRAGGING   
        if uievent.eventtype == 'mousedrag':
            if uievent.selected.item is None:
                #print("what a drag")
                return ng.BackgroundMouseHandler(uievent)
                
        #------------------------------------------- CALL DEFAULT HANDLER       
        return ng.NodeMouseHandler.handleEvent(self, uievent, pending_actions)
            
            

#-------------------------------------------Mouse Wheel Handler -------------------------------------------

class MouseWheelHandler(ng.NodeMouseHandler):
    def handleEvent(self, uievent, pending_actions):
        # distributes wheel events
        # to its respective subroutines        
        editor = uievent.editor
        
        if isinstance(uievent, MouseEvent):
            wheel_direction = "down" if uievent.wheelvalue > 0 else "up" if uievent.wheelvalue < 0 else "None"             
            # CTRL --> wheeldiving  
            if not uievent.modifierstate.shift and uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                wheelDiving(uievent, editor, wheel_direction)
            # SHIFT only --> jump back/forward (NEW)
            elif uievent.modifierstate.shift and not uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                widget = QtWidgets.QApplication.focusWidget()
                if widget:
                    if wheel_direction == "up":
                        key = QtCore.Qt.Key_Left
                    elif wheel_direction == "down":
                        key = QtCore.Qt.Key_Right
                    else:
                        key = None
                    if key:
                        press = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, QtCore.Qt.AltModifier)
                        release = QtGui.QKeyEvent(QtCore.QEvent.KeyRelease, key, QtCore.Qt.AltModifier)
                        QtWidgets.QApplication.sendEvent(widget, press)
                        QtWidgets.QApplication.sendEvent(widget, release)
            # SHIFT + CTRL --> scale nodeshapes
            elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                wheelNodeScaling(uievent, editor, wheel_direction)
            # ALT --> change node colors
            elif not uievent.modifierstate.shift and not uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                wheelChangeNodecolor(uievent, editor, wheel_direction)   
            # CTRL + ALT --> change node shapes
            elif not uievent.modifierstate.shift and uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                wheelChangeNodeshape(uievent, editor, wheel_direction)
            # SHIFT + ALT --> nothing
            #elif uievent.modifierstate.shift and not uievent.modifierstate.ctrl and uievent.modifierstate.alt:
            #    wheelChangeNodecolor(uievent, editor, wheel_direction)
            else:
            # NO MODIFIER --> default behaviour  
                view.scaleWithMouseWheel(uievent)




#------------------------------------------- MODIFIED CLASSES -------------------------------------------

# original classes are in nodegraph.py                
# we extend its functionality by adding information of the last event
class NodeConnectionMouseHandler_huxel(base.ItemEventHandler):
    def __init__(self, uievent, last_uievent):
            super(NodeConnectionMouseHandler_huxel, self).__init__(uievent)
            self.last_uievent = last_uievent
    def handleEvent(self, uievent, pending_actions):
        if uievent.selected.name == 'wire':
            handler = NodeWireMouseHandler_huxel(uievent, self.last_uievent)
        else:
            handler = NodeWireStubMouseHandler(uievent)
        return handler.handleEvent(uievent, pending_actions)

# original classes are in nodegraph.py
# by this time the original mousedown event has already been consumed
# thats why we extend its functionality to be able to look back to the last (mousedown) event
class NodeWireMouseHandler_huxel(base.ItemEventHandler):
    #added
    def __init__(self, uievent, last_uievent=None):
            super(NodeWireMouseHandler_huxel, self).__init__(uievent)
            self.last_uievent = last_uievent
    def handleEvent(self, uievent, pending_actions):
        # Check if the user wants to enter the scroll state.
        if states.isScrollStateEvent(uievent):
            return states.ScrollStateHandler(uievent, self)
        #modified/added start
        editor = self.last_uievent.editor
        last_action = self.last_uievent.eventtype

        if uievent.eventtype == 'mouseup' and last_action == 'mousedown':
            if uievent.modifierstate.alt and self.last_uievent.mousestate.lmb and \
                utils.supportsNetworkDots(editor.pwd()):
                #modified/added end
                with hou.undos.group('Create dot', editor):
                    dot = editor.pwd().createNetworkDot()
                    dot.setPosition(editor.posFromScreen(uievent.mousepos))
                    dot.setInput(self.item.inputItem(),
                        self.item.inputItemOutputIndex())
                    self.item.outputItem().setInput(self.item.inputIndex(),
                        dot, 0)
                    handler = ng.NetworkDotMoveHandler(self.start_uievent, None)
                    handler.item = dot
                    utils.cleanupDisconnectedItems(editor.pwd())
                    return handler

            elif self.start_uievent.mousestate.rmb:
                menu = popupmenus.WireContextMenu(uievent, uievent.located.item)
                result = utils.getPopupMenuResult(menu)
                result = menu.executeCommand(result)
                if isinstance(result, base.EventHandler):
                    return result

                return None

        elif uievent.eventtype == 'mousedrag':
            handler = None
            if self.start_uievent.mousestate.lmb:
                handler = connect.WireConnectHandler(uievent)
            elif base.isPanEvent(self.start_uievent):
                handler = base.ViewPanHandler(self.start_uievent)
            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)
            if handler:
                return handler.handleEvent(uievent, pending_actions)

        elif uievent.eventtype == 'mouseup':
            if self.start_uievent.selected.item == uievent.located.item:
                if self.start_uievent.mousestate.lmb and \
                     uievent.modifierstate.alt:
                    handler = connect.WireMenuConnectHandler(
                                        self.start_uievent,
                                        [self.item],
                                        False)
                    return handler.handleEvent(uievent, pending_actions)

                elif self.start_uievent.mousestate.lmb:
                    view.modifySelection(uievent, None, [self.item])

            return None

        # Keep handling events until a mouse action is identified.
        return self