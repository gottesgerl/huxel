import hou

def test():
    print("success.")

def convertToBox(**kwargs):
    node = hou.node(kwargs["path"])
    parent = node.parent()
    box = node.parent().createNode("box")
    box.setInputsFromData(node.inputsAsData())
    box.setOutputsFromData(node.outputsAsData())
    box.setPosition(node.position())
    #size = node.geometry().boundingBox().sizevec()
    #center = node.geometry().boundingBox().center()
    box.parmTuple("size").set(tuple([r*2 for r in node.parmTuple("rad").eval()]))
    box.parmTuple("t").set(node.parmTuple("t").eval())
    box.parmTuple("r").set(node.parmTuple("r").eval())
    box.parm("scale").set(node.parm("scale").eval())
    if node.isDisplayFlagSet(): box.setDisplayFlag(1)
    if node.isRenderFlagSet(): box.setRenderFlag(1)
    if node.isDisplayFlagSet(): box.setSelected(1)
    node.destroy()