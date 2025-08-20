import hou

def test():
    print("success.")
    
def setInput(value, **kwargs):
    node = hou.node(kwargs["path"])
    num_connections = len(node.inputs())
    if (num_connections < value+1): hou.ui.setStatusMessage("Input %s NOT connected." %(value+1), severity=hou.severityType.ImportantMessage)   
    else:    node.parm('input').set(value)