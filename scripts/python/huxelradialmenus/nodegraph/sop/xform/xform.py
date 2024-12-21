import hou
import mouseevents

    
def setCentroid(**kwargs):
    # set the pivot to the current centroid
    node = hou.node(kwargs["path"])
    geo = node.geometry()
    if geo: 
        center=geo.boundingBox().center()
        node.parmTuple("p").set(center)