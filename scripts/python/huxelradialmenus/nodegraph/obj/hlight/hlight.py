import hou
import mouseevents
import huxelradialmenus.sceneviewer.sceneviewertools as viewertools
import huxelradialmenus.commontools as commontools


def lookThroughCamera(**kwargs):
    cam = hou.node(kwargs["path"])
    viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    viewport = viewer.curViewport()
    viewport.setCamera(cam)

def lockCameraXformToggle(**kwargs):
    cam = hou.node(kwargs["path"])
    parms = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")
    state = cam.parm(parms[0]).isLocked()
    for parm in parms: cam.parm(parm).lock(1-state)  
    
    
def lookAndLock(**kwargs):
    lookThroughCamera(lockToView=False, **kwargs)
    viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    viewport = viewer.curViewport()
    if viewport.camera():        
        state = viewport.isCameraLockedToView()
        viewport.lockCameraToView(1-state)    