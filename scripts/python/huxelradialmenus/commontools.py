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
    

def getClosestNode():
    p = paneinfo()
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(p.get("panetab"))
    pane_size = p.get("pane_size")
    parent = p.get("parent")
    context = p.get("context")
    cursorpos = p.get("cursor_position")
    # Get closest node  
    pos1 = hou.Vector2(0,0)
    pos2 = hou.Vector2(pane_size[0], pane_size[1])
    allItems = editor.networkItemsInBox(pos1, pos2, for_drop="False", for_select="False")
    allNodes = [ i[0] for i in allItems if i[1]=='node']
    allDistances = { i:i.position().distanceTo(hou.Vector2(cursorpos)) for i in allNodes }
    nodesByDistance = {k: v for k, v in sorted(allDistances.items(), key=lambda item: item[1])}
    if not nodesByDistance: 
        kwargs = {"path":None, "distance":9999, "context":context, "editor":editor.name(), "cursorpos":cursorpos}
    else:
        node = list(nodesByDistance.keys())[0]
        distance = list(nodesByDistance.values())[0]
        nodetype = node.type()
        path = node.path()
        #presets = hou.hscript("oppresetls %s" %node.path())[0].split("\n")
        kwargs = {"path":path, "distance":distance, "context":context, "editor":editor.name(), "cursorpos":cursorpos}
    return kwargs

        
def createNode(nodetype, connect=1, display=1, select=1, good_position=1, **kwargs):
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