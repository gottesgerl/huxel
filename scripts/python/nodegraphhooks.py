import hou
from canvaseventtypes import *
import mouseevents
from importlib import reload
import nodegraph

# As this code gets loaded only while starting houdini, 
# we just use it to reload and kick off the actual scripts
        
def createEventHandler(uievent, pending_actions):
    reload(mouseevents)
    if isinstance(uievent, MouseEvent) and uievent.eventtype == 'mousewheel': 
        return mouseevents.MouseWheelHandler(uievent), True
    if isinstance(uievent, MouseEvent) and uievent.eventtype == 'mousedown'  and uievent.mousestate.lmb:
        return mouseevents.LmbMouseHandler(uievent), True

    return None, False