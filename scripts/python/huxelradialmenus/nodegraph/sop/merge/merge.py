import hou

def test():
    print("success.")
    
    
def convertToSwitch(kwargs):
    node = hou.node(kwargs["path"])
    parent = node.parent()
    switch = node.parent().createNode('switch')
    for i in node.inputs(): switch.setNextInput(i)    
    switch.setPosition(node.position())
    switch.setDisplayFlag(1)
    switch.setSelected(1)
    node.destroy()