import hou
import os
import json
import radialmenu
import importlib
import nodeselectionutil
import toolutils

def paneinfo():
    # Collect pane info
    desktop = hou.ui.curDesktop()
    pane = hou.ui.paneUnderCursor()
    panetab = pane.currentTab()
    panetabtype = panetab.type().name()
    pane_size = panetab.size()    
    path = panetab.pwd().path()
    kwargs = {"panetab":panetab.name(), "panetabtype":panetabtype, "pane_size":pane_size, "path":path}
    if panetabtype == "NetworkEditor": 
        cp = panetab.cursorPosition(confine_to_view=False)
        cp_screen = panetab.posToScreen(cp)
        parent = hou.node(path)
        context = parent.childTypeCategory().name()[:3].lower()
        kwargs_addinfo = {"context":context, "cursor_position":[cp.x(), cp.y()], "cursor_screen_position": [cp_screen.x(), cp_screen.y()]}        
    elif panetabtype == "SceneViewer":
        viewport = panetab.curViewport()
        viewertype = panetab.pwd().type().name()
        camera = viewport.camera()
        camera_path = viewport.cameraPath()
        kwargs_addinfo = {"viewport":viewport.name(), "viewertype":viewertype, "camera_path":camera_path}
    kwargs.update(kwargs_addinfo)
    return kwargs
    

def getClosestNode(max_distance=2.5):
    p = paneinfo()
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(p.get("panetab"))
    pane_size = p.get("pane_size")
    context = p.get("context")
    cursorpos = p.get("cursor_position")
    cp = hou.Vector2(cursorpos)

    # Get closest node
    pos1 = hou.Vector2(0, 0)
    pos2 = hou.Vector2(pane_size[0], pane_size[1])
    allItems = editor.networkItemsInBox(pos1, pos2, for_drop=False, for_select=True)
    allNodes = [i[0] for i in allItems if i[1] == 'node']

    # distance to the node's boundary -> 0.0 means the cursor is on the node
    allDistances = {i: editor.itemRect(i).closestPoint(cp).distanceTo(cp) for i in allNodes}
    ranked = sorted(allDistances.items(), key=lambda item: item[1])

    if not ranked:
        return {"path": None, "distance": 9999, "hit": "none",
                "context": context, "editor": editor.name(), "cursorpos": cursorpos}

    node, distance = ranked[0]
    if   distance == 0.0:          hit = "exact"
    elif distance <= max_distance: hit = "close"
    else:                          hit = "none"

    return {"path": node.path(), "distance": distance, "hit": hit,
            "context": context, "editor": editor.name(), "cursorpos": cursorpos}

        
def createNode(nodetype, connect=1, display=1, select=1, good_position=1, **kwargs):
    #creates a node and deals with connections, flags and positions
    if "path" in kwargs.keys():
        node = hou.node(kwargs["path"])
    else: 
        print("No path found. Taking OBJ-Context instead.")
        node = hou.node("/obj")
    is_manager = 1 if node.type().category().name() == "Manager" else 0
    
    if is_manager:   parent = node
    else:            parent = node.parent()
    newnode = parent.createNode(nodetype)
    desktop = hou.ui.curDesktop()
    if "panetab" in kwargs:    editor = desktop.findPaneTab(kwargs["panetab"])
    if "name" in kwargs: newnode.setName(name, 1)
    if "parms" in kwargs: print("PARMS")
    if "inputs" in kwargs: print("INPUTS")
    if "outputs" in kwargs: print("OUTPUTS")
    if not "inputs" in kwargs:
        if connect: newnode.setNextInput(node)
    if not is_manager:
        if parent.displayNode() == parent.renderNode(): newnode.setRenderFlag(1)
        if display: newnode.setDisplayFlag(1)    
    if select: fullSelectNode(newnode.path())
    if good_position: newnode.moveToGoodPosition(move_inputs = False, move_outputs = False, move_unconnected = False)
    return newnode

def convertNode(nodetype, connect=1, display=0, select=0, **kwargs):
    #replaces a given node by a new one with different type
    node = hou.node(kwargs["path"])
    parent = node.parent()
    newnode = node.parent().createNode(nodetype)
    houversion = hou.applicationVersion()
    if houversion[0]>=20 and houversion[1]>=5:
        #hou 20.5 only
        newnode.setInputsFromData(node.inputsAsData())
        newnode.setOutputsFromData(node.outputsAsData())
    else:
        for i in node.inputs(): newnode.setNextInput(i)
        for o in node.outputConnections():   o.outputNode().setInput(o.inputIndex(), newnode)
    newnode.setPosition(node.position())
    if display: newnode.setDisplayFlag(1)
    if select: newnode.setSelected(1)
    node.destroy()


def clipboard_to_objmerge(display=0, **kwargs):
    #creates object_merge-nodes based on the current clipboard
    network = hou.ui.curDesktop().paneTabUnderCursor()
    parent = network.pwd().path()
    mouse_pos = network.cursorPosition()
    clipboard = hou.ui.getTextFromClipboard()
    prefix = "IN_"
    offset = 0.0
    offset_min = 1
    offset_per_letter = .1
    nodes = []
    if clipboard:
        list = clipboard.split()
        for item in list:
            node = hou.node(item)
            if node != None:
                obj_merge = hou.node(parent).createNode('object_merge',prefix+node.name())
                obj_merge.parm('objpath1').set(node.path())
                obj_merge.setPosition(mouse_pos)
                obj_merge.move([len(nodes)*offset_min,0])
                obj_merge.move([offset,0])
                offset += obj_merge.size()[0]+(len(obj_merge.name())*offset_per_letter)
                if not len(nodes): obj_merge.setSelected(True, True)
                else:              obj_merge.setSelected(True, False)
                obj_merge.setDisplayDescriptiveNameFlag(False)
                nodes.append(obj_merge)            
    if not len(nodes): hou.ui.setStatusMessage("No nodes found in clipboard. Please copy (ctrl+c) a node/nodes to the clipboard first.", hou.severityType.ImportantMessage)

def create_objmerge_in_new_geo(new_geo=False, display=1, connect=0, select=1, good_position=0, hide_badges=1, **kwargs):
    # creates a new geometry node and jumps into it
    node = hou.node(kwargs["path"])
    editor = hou.ui.curDesktop().findPaneTab(kwargs["editor"])    
    parent = node.parent()    
    position_offset = hou.Vector2(0,-1)
    newpos = node.position()+position_offset    
    if 'OUT' in node.name():    newname = node.name().replace('OUT', 'IN')
    else:                       newmame = 'IN_'+node.name()
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

def fullSelectNode(nodepath):
    node = hou.node(nodepath)
    desktop = hou.ui.curDesktop()
    scene_viewer = toolutils.sceneViewer()
    # to update Parameter Values and Network Editors we have to check if they are linked
    # if all of one type are linked, we temporarily unlink them 
    #editortypes = (hou.paneTabType.Parm, hou.paneTabType.NetworkEditor)
    editortypes = (hou.paneTabType.Parm, hou.paneTabType.NetworkEditor, )
    for editortype in editortypes:
        panetabs = desktop.currentPaneTabs()
        all_network_editors = [panetab for panetab in panetabs if panetab.type() == editortype]
        networks = {}
        for network_editor in all_network_editors:
            link = network_editor.linkGroup().name()
            networks[link] = network_editor
        #find lowest group link
        network = None
        if not "FollowSelection" in networks.keys():
            for i in range(9):
                if ("Group%s" %i) in networks.keys(): 
                    network = networks[("Group%s" %i)]; 
                    group_num = i; 
                    break
        if network:
            #unlink
            network.setLinkGroup(hou.paneLinkType.FollowSelection)
            node.setSelected(1, clear_all_selected=True)
            node.setCurrent(1, 1)
            scene_viewer.setPwd(node.parent())
            toolutils.homeToSelectionNetworkEditorsFor(node.parent())  
            
            #hou.ui.triggerUpdate()
            #nodeselectionutil.prepareNetworkView()
            #nodeselectionutil.setNodeSelected(node.path())
            
            #relink
            network.setLinkGroup(eval("hou.paneLinkType.Group%s" %i))


def buildMenuFromJsonFile(nodepath, **kwargs):    
    #build menu from json file   
    node = hou.node(nodepath)
    context = node.parent().childTypeCategory().name()[:3].lower()
    ntype = node.type().name()
    huxelpath = hou.getenv("Huxel")
    modulepath = ("huxelradialmenus.nodegraph.%s.%s.%s" %(context, ntype, ntype))    
    file = "%s/scripts/python/%s.json" %(huxelpath, modulepath.replace(".", "/"))
    if os.path.isfile(file):  
        menu = {}            
        with open(file, "r") as json_file:
            input = json.load(json_file)    
            for dir, values in input.items():
                menu[dir] = {}
                for value in values:
                    for k, v in value.items():
                        #import modules
                        if k == "script":
                            if os.path.isfile(file.replace(".json", ".py")):
                                module = importlib.import_module(modulepath)
                            v=v.replace("kwargs", str(kwargs))
                            viewertools = importlib.import_module("huxelradialmenus.sceneviewer.sceneviewertools")
                            commontools = importlib.import_module("huxelradialmenus.commontools")
                        menu[dir][k]=v
    radialmenu.setRadialMenu(menu)
    return radialmenu

def useRecipe(name, type="NodePreset", **kwargs):
    node = hou.node(kwargs["path"])
    hou_preRecipeVersion = int("".join(map(str, hou.applicationVersion())))<205000
    #Houdini 20.0 and below
    if hou_preRecipeVersion:
            presets = hou.hscript("oppresetls %s" %node.path())[0].split("\n")
            presetname_raw = hou.hda.componentsFromFullNodeTypeName(name)[2]
            presetname_whitespaces = presetname_raw.replace("_", " ")
            presetname_formatted = "(%s)%s" %(presetname_whitespaces[0], presetname_whitespaces[1:])
            if presetname_raw in presets: hou.hscript("oppresetload %s \"%s\"" %(node.path(), presetname_raw))
            elif presetname_formatted in presets: hou.hscript("oppresetload %s \"%s\"" %(node.path(), presetname_formatted))
            else: print("Preset %s not found." %name)
    #Houdini 20.5 and above
    else:
        if (type == "NodePreset"):
            hou.data.applyNodePresetRecipe(name=name, node=node)

def useLegacyPreset(name, **kwargs):
    node = hou.node(kwargs["path"])
    presets = hou.hscript("oppresetls %s" %node.path())[0].split("\n")
    presetname_raw = hou.hda.componentsFromFullNodeTypeName(name)[2]
    presetname_whitespaces = presetname_raw.replace("_", " ")
    presetname_formatted = "(%s)%s" %(presetname_whitespaces[0], presetname_whitespaces[1:])
    if presetname_raw in presets: hou.hscript("oppresetload %s \"%s\"" %(node.path(), presetname_raw))
    elif presetname_formatted in presets: hou.hscript("oppresetload %s \"%s\"" %(node.path(), presetname_formatted))
    else: print("Preset %s not found." %name)
    
def radialMenuScan(radialmenu):
    #positions = [hou.radialItemLocation.Top, hou.radialItemLocation.TopRight, hou.radialItemLocation.Right, hou.radialItemLocation.BottomRight, hou.radialItemLocation.Bottom, hou.radialItemLocation.BottomLeft, hou.radialItemLocation.Left, hou.radialItemLocation.TopLeft]
    positions = [hou.radialItemLocation.TopRight,]
    free_positions = [0,0,0,0,0,0,0,0]
    for i, p in enumerate(positions):         
        if radialmenu.root().item(p): free_positions[i] = 1
    return free_positions

def shortcutMap():
    shortcut_mapping = {"n":"W", "ne":"E", "e":"D", "se":"X", "s":"X", "sw":"Z", "w":"A", "nw":"Q"}
    return shortcut_mapping
   
def createShortcutMap(slots):
    shortcut_mapping = shortcutMap()
    shortcuts = [""]*8
    for i, s in enumerate(slots):   shortcuts[i] = shortcut_mapping[s]
    return shortcuts