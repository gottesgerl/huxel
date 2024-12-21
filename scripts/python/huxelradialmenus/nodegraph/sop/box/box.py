import hou

def test():
    print("success.")

def convertToSphere(**kwargs):
    node = hou.node(kwargs["path"])
    parent = node.parent()
    sphere = node.parent().createNode("sphere")
    sphere.setInputsFromData(node.inputsAsData())
    sphere.setOutputsFromData(node.outputsAsData())
    sphere.setPosition(node.position())
    sphere.parmTuple("rad").set(tuple([r*0.5 for r in node.parmTuple("size").eval()]))
    sphere.parmTuple("t").set(node.parmTuple("t").eval())
    sphere.parmTuple("r").set(node.parmTuple("r").eval())
    sphere.parm("scale").set(node.parm("scale").eval())
    if node.isDisplayFlagSet(): sphere.setDisplayFlag(1)
    if node.isRenderFlagSet(): sphere.setRenderFlag(1)
    if node.isDisplayFlagSet(): sphere.setSelected(1)
    node.destroy()