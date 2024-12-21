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
        
def setHuxelMainCam(prio, **kwargs):
    #first we unmount all cameras with the same priority
    for cam in hou.node("/obj").allSubChildren():
        if (cam.parm("huxel_maincam")):
            slot = cam.parm("huxel_maincam").eval()
            if slot==prio:
                cam.parm("huxel_maincam").set(-1)
    #now we set the new camera            
    cam = hou.node(kwargs["path"])
    if (cam.parm("huxel_maincam")):
        slot = cam.parm("huxel_maincam").eval()
    #if huxel main cam parameter does not exists - create it
    else:
        ptg = cam.parmTemplateGroup()
        parm = hou.IntParmTemplate("huxel_maincam", "Huxel Main Cam", 1, default_value=[-1], min=-1, max=2)
        ptg.append(parm)
        cam.setParmTemplateGroup(ptg)
        slot=-1
    cam.parm("huxel_maincam").set(prio)
    hou.ui.setStatusMessage("Camera Set.", hou.severityType.Message)

