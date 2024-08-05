import hou
from PySide2 import QtCore
from PySide2.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
import huxelradialmenus.commontools as commontools
import os
import radialmenu


verbose = 0


# update Dialog Window (Qt)
def getHoudiniMainWindow():
    return hou.qt.mainWindow()

class updateDialog(QMainWindow):
    def __init__(self, parent=getHoudiniMainWindow()):
        super(updateDialog,self).__init__(parent)
        
        self.setWindowTitle("Manual Update Mode")
        self.setMinimumSize(300, 80)
        
        button_update = QPushButton("Trigger Update Once")
        button_update.clicked.connect(self.triggerUpdate)
       
        button_set_auto = QPushButton("Switch Auto Update")
        button_set_auto.clicked.connect(self.setAutoUpdate)
        
        button_noupdate = QPushButton("Skip")
        button_noupdate.clicked.connect(self.close)
        
        message = QLabel("Changes will be visible after next update", alignment=QtCore.Qt.Alignment(4))
        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addWidget(button_update)
        layout.addWidget(button_set_auto)
        layout.addWidget(button_noupdate)
        
        widget = QWidget()
        widget.setLayout(layout)
        
        self.setCentralWidget(widget)        
        
    def triggerUpdate(self):
        hou.ui.triggerUpdate()
        self.close()
        
        
    def setAutoUpdate(self):
        hou.setUpdateMode(hou.updateMode.AutoUpdate)
        self.close()
        
def getDownstreamNodes(node):
        downstreamnodes = []
        for n in node.outputs():
            downstreamnodes.append(n)
            getDownstreamNodes(n)
        return downstreamnodes
    

def getCameras(kwargs):
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(kwargs["panetab"])
    viewertype = kwargs["viewertype"]
    path = editor.pwd()
    cams=[]
    #LOPS
    if viewertype == "stage":         
        displayedNode = path.displayNode()
        # get all up- and downstreamnodes 
        # there surely is a better way to find all cameras 
        # please redo 
        upstreamnodes = displayedNode.inputAncestors()    
        downstreamnodes = getDownstreamNodes(displayedNode)
        allnodes = [displayedNode]
        allnodes += upstreamnodes + tuple(downstreamnodes)    
        for an in allnodes:
            if an.type().name() == "camera":
                cam_primpath = cam.parm("primpath").eval()
                cams.append(cam_primpath)
    #OBJ
    else:
        obj_category = hou.nodeTypeCategories()["Object"]
        nodetype = hou.nodeType(obj_category, "cam")
        cams.extend(nodetype.instances())
    return cams

def newCamera(kwargs):
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(kwargs["panetab"])
    viewport = editor.curViewport()
    newcam = hou.node("/obj").createNode("cam")
    newcam.moveToGoodPosition()
    viewport.saveViewToCamera(newcam)
    viewport.setCamera(newcam)
    
    '''
    #LOP fragments:
    # Record the viewport xform before creating the new LOP. This is in case
    # this tool is invoked from with a SOP network inside the LOP network.
    # The viewport xform changes when we jump up to create the LOP node.
    if not clicktoplace and isinstance(activepane, hou.SceneViewer):
        viewport_xform = activepane.curViewport().viewTransform()

    # Create the requested LOP node.
    camlight = genericTool(scriptargs, nodetypename, nodename,
                           clicktoplace = clicktoplace)

    if not clicktoplace and isinstance(activepane, hou.SceneViewer):
        # Re-fetch the viewport from the scene viewer, as we may have changed
        # from a SOP viewer to a LOP viewer when we created the LOP node.
        viewport = activepane.curViewport()
        saveViewXformToCamera(viewport, viewport_xform, camlight)
        viewport.setCamera(camlight.parm('primpath').eval())
        viewport.lockCameraToView(lock_to_view)
    '''
    
    
def selectCamera(**kwargs):
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(kwargs["panetab"])
    cam = hou.node(kwargs["cam"])
    commontools.fullSelectNode(cam.path())
            
def lookThroughCamera(lockToView=True, **kwargs):
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(kwargs["panetab"])
    cam = hou.node(kwargs["cam"])
    #viewport = e.findViewport(kwargs["viewport"])    
    viewport = editor.curViewport()
    viewport.setCamera(cam)
    if lockToView: viewport.lockCameraToView(0)    
    if ( hou.updateModeSetting() == hou.updateMode.Manual):
        window = viewertools.updateDialog()
        window.show()        
        
def lockCameraViewToggle(**kwargs):
    lookThroughCamera(lockToView=False, **kwargs)
    desktop = hou.ui.curDesktop()
    editor = desktop.findPaneTab(kwargs["panetab"])
    viewport = editor.curViewport()
    if viewport.camera():        
        state = viewport.isCameraLockedToView()
        viewport.lockCameraToView(1-state)       
        
def lockCameraXformToggle(**kwargs):
    lookThroughCamera(lockToView=False, **kwargs)
    selectCamera(**kwargs)
    cam = hou.node(kwargs["cam"])
    parms = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")
    state = cam.parm(parms[0]).isLocked()
    for parm in parms: cam.parm(parm).lock(1-state)

def createLookAtCamera(**kwargs):    
    hou.ui.setStatusMessage("To be done.", hou.severityType.ImportantMessage)    
        
def getAllLights(**kwargs):
    area_lighttypes = ("hlight::2.0", "rslight")
    dome_lighttypes = ("envlight", "rslightdome::2.0")
    desktop = hou.ui.curDesktop()
    viewer = desktop.findPaneTab(kwargs["panetab"])
    viewertype = kwargs["viewertype"]
    area_lights = ()
    dome_lights = ()
    #LOPS
    if viewertype == "stage":
        hou.ui.setStatusMessage("To be done.", hou.severityType.ImportantMessage)            
    #OBJ
    else:
        for area_lighttype in area_lighttypes:      area_lights = area_lights+hou.objNodeTypeCategory().nodeType(area_lighttype).instances()
        for dome_lighttype in dome_lighttypes:      dome_lights = dome_lights+hou.objNodeTypeCategory().nodeType(dome_lighttype).instances() 
    return area_lights, dome_lights

def lightsSubmenu(**kwargs):    
    menu = {}     
    area_lights, dome_lights = getAllLights(**kwargs)
    if not dome_lights:
        submenu = ("viewertools.domelightSubmenu(**%s)" %(kwargs))
        menu["e"]={
            "type": "script_submenu",
            "label": "New Dome light",
            "icon": "OBJ_camera",
            "script": submenu,
            "shortcut": "D"         }
    else:
        cmd = ("commontools.fullSelectNode('%s')" %dome_lights[0].path())
        menu["e"]={
            "type": "script_action",
            "label": dome_lights[0].name(),
            "icon": "OBJ_camera",
            "script": cmd,
            "shortcut": "D"         }
    radialmenu.setRadialMenu(menu)
    return radialmenu
    

def domelightSubmenu(**kwargs):
    menu = {}    
    kwargs["path"] = "/obj"
    #RS Domelight
    cmd="commontools.createNode('rslightdome::2.0', connect=0, display=0, select=1, **%s)" %kwargs
    menu["ne"]={
            "type": "script_action",
            "label": "New RS Domelight",
            "icon": "OBJ_camera",
            "script": cmd,
            "shortcut": "E"         }
    #Houdini Envlight
    cmd="commontools.createNode('envlight', connect=0, display=0, select=1, **%s)" %kwargs        
    menu["se"]={
            "type": "script_action",
            "label": "New Env Light",
            "icon": "OBJ_camera",
            "script": cmd,
            "shortcut": "C"         }
    radialmenu.setRadialMenu(menu)
    return radialmenu

    
def selectionToogle(**kwargs):
    desktop = hou.ui.curDesktop()
    viewer = desktop.findPaneTab(kwargs["panetab"])
    viewport = viewer.curViewport()
    #editor.selectGeometry()
    state = viewer.currentState()
    viewer.setCurrentState("select")
    '''
    if state != "select":        
        viewer.setCurrentState("select")
        viewer.setSelectionMode(hou.selectionMode.Geometry)
    else:                        
        viewer.enterViewState()
        viewer.setSelectionMode(hou.selectionMode.Object)
    '''