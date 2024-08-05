from __future__ import print_function
from __future__ import division
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
    parent = editor.pwd()
    context = parent.childTypeCategory().name()
    if context == "Sop":
        if parent.displayNode() == parent.renderNode(): node.setRenderFlag(True)
        node.setDisplayFlag(True)
    elif context == "Object":
        node.setDisplayFlag(abs(node.isDisplayFlagSet()-1))

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
                if not c: fo.setGenericFlag(hou.nodeFlag.DisplayComment, False)
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
        for n in range(len(cycle_nodes)):
            if cycle_nodes[n]==displayNode:
                setDisplayFlags(editor, cycle_nodes[(n+1)%len(cycle_nodes)])
    
def shadedTemplate(editor, node):
    # toggles shaded template flag
    # turns of template flag together with selectable template flag
    value = abs(node.isSelectableTemplateFlagSet()-1)
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
    path = node.parm("objpath1").evalAsNodePath()
    target = hou.node(path)
    centerNode(editor, target)
    setSelection(editor, target)
    #editor.homeToSelection()


def handle_SOPnull(editor, node):
    # NULL 
    # go to dependent nodes
    targets = node.dependents()
    if targets:
        target = targets[0]
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


def wheelDiving(uievent, editor, wheel_direction):
    # Move one level up or dive
    # into the node under pointer
    block_managers = 0
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


def wheelNodeScaling(uievent, editor, wheel_direction):
    # scale node shapes
    all_shapes = editor.nodeShapes()
    if uievent.located.item != None:
        node = hou.node(uievent.located.item.path())
        nodeshape = node.userData("nodeshape")
        #get default shape for nodetype
        if not nodeshape: nodeshape = node.type().defaultShape()
        if not nodeshape: nodeshape ="rect"
        default_shape = nodeshape
        new_shape = ""
        if not nodeshape:       nodeshape = node.type().defaultShape()
        all_shapes = editor.nodeShapes()
        size_token = re.findall("[_]([sl])([\d])$", nodeshape)
        size = ""
        step = 0
        #We found a custom size
        if size_token:
            if len(size_token[0])==2:
                size = size_token[0][0]
                step = int(size_token[0][1])
                default_shape = nodeshape.replace(("_"+size+str(step)), "")
        else: 
            size = "d"
            step = 1
            
        if wheel_direction == "up":           
            if size=="s": step -= 1
            elif size=="l": step += 1
            else: size="l"      
            #print("Make Bigger %s --> Size: %s --> Step: %s --> Default Shape: %s" %(nodeshape, size, step, default_shape))            

        elif wheel_direction == "down":    
            if size=="s": step += 1
            elif size=="l": step -= 1
            else: size="s"            
            #print("Make Smaller %s --> Size: %s --> Step: %s --> Default Shape: %s" %(nodeshape, size, step, default_shape))               
        
        #if step = 0 use default shape
        if step==0: new_shape = default_shape
        else:       new_shape = default_shape+"_"+size+str(step)
        #print("Original: %s --> --> Size: %s --> Step: %s --> New: %s" %(nodeshape, size, step, new_shape))
        
        if new_shape in all_shapes:
            node.setUserData("nodeshape", new_shape)

'''   
    cur_shape = s.userData("nodeshape")


    #setting back to default color and shape
    if (cur_color == vis_color) and (cur_shape == vis_shape):
        counter_devis += 1
        default_color = s.type().defaultColor()
        default_shape = s.type().defaultShape()
        s.setColor(default_color)
        s.setUserData("nodeshape", default_shape)
'''

#-------------------------------------------Left Mouse Button Handler -----------------------------------   

  
class LmbMouseHandler(ng.NodeMouseHandler):

    def handleEvent(self, uievent, pending_actions):
        # the main event handler which
        # distributes each mouse event
        # to its respective subroutines
        
        editor = uievent.editor
                
        if isinstance(uievent, MouseEvent):
            if uievent.selected.item is not None:
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
                    else:                               max_distance = 2.5
                    
                    nodes = getVisibleNodes(uievent, max_distance)
                    if nodes:
                        closest_node = nodes[0]
                        parent = editor.pwd()
                        context = parent.childTypeCategory().name()
                        
                        # SHIFT --> set selection and display flag    
                        if uievent.modifierstate.shift and not uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                             if context == "Sop":        
                                editor.setCurrentNode(closest_node)                        
                                setDisplayFlags(editor, closest_node)   
                                              
                        # SHIFT + CTRL --> cycle stored nodes / add to selection
                        elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                            if context == "Sop":        viewCycle(editor)
                            if context == "Object":     closest_node.setSelected(True)
                                                                             
                        # SHIFT + ALT --> nothing
                        elif uievent.modifierstate.shift and not uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                            pass
                            
                        # SHIFT + ALT + CTRL --> store view selection
                        elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and uievent.modifierstate.alt:
                            if context == "Sop":        storeViewCycle(editor)
                            
                        # CTRL ONLY -->  set display flag   
                        elif uievent.modifierstate.ctrl and not uievent.modifierstate.alt and not uievent.modifierstate.shift:
                            setDisplayFlags(editor, closest_node)
                        
                        # ALT --> toogle template flag / remove from selection                 
                        elif uievent.modifierstate.alt and not uievent.modifierstate.ctrl and not uievent.modifierstate.shift:
                            if context == "Sop":        closest_node.setTemplateFlag(abs(closest_node.isTemplateFlagSet()-1))
                            if context == "Object":    closest_node.setSelected(False)
                            
                        # ALT + CTRL --> toogle shaded template mode
                        elif uievent.modifierstate.alt and uievent.modifierstate.ctrl and not uievent.modifierstate.shift:
                            if context == "Sop":        shadedTemplate(editor, closest_node)
                                                        
                        # NO MODIFIER --> set selection      
                        else:
                            setSelection(editor, closest_node)

                            
                           
                            
                 #-------------------------------------------double clicking a NODE
                else:
                    node =  uievent.selected.item
                    type = node.type()
                    
                    if type == hou.nodeType(hou.sopNodeTypeCategory(), "object_merge"):                        
                        handle_SOPobjectMerge(editor, node)

                    if type == hou.nodeType(hou.sopNodeTypeCategory(), "null"):
                        handle_SOPnull(editor, node)
                        
                    if type == hou.nodeType(hou.sopNodeTypeCategory(), "switch"):
                        handle_SOPswitch(uievent, editor, node)
                        
        
        #------------------------------------------- HANDLING OVERLAYS AND SPECIFIC CASES      
                    
            elif uievent.selected.name == 'colorpalettecolor':
                return palettes.ColorPaletteMouseHandler(uievent)
            elif uievent.selected.name == 'shapepaletteshape':
                return palettes.ShapePaletteMouseHandler(uievent)
            elif uievent.selected.name in ('taskgraphworkitem', 'taskgraphcollapseditem'):
                return WorkItemMouseHandler(uievent)
            elif uievent.selected.name == 'taskgraphpage':
                return TaskGraphPageHandler(uievent)
            elif uievent.selected.name == 'taskgraphopentable':
                return TaskGraphSeeMoreHandler(uievent)
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
                return IndirectInputMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NetworkDot):
                return ng.NetworkDotMouseHandler(uievent)
            elif isinstance(uievent.selected.item, hou.NodeConnection):
                return ng.NodeConnectionMouseHandler(uievent)
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
            # SHIFT + CTRL --> scale nodeshapes  
            elif uievent.modifierstate.shift and uievent.modifierstate.ctrl and not uievent.modifierstate.alt:
                wheelNodeScaling(uievent, editor, wheel_direction)
            else:
            # NO MODIFIER --> default behaviour  
                view.scaleWithMouseWheel(uievent)
            
                
