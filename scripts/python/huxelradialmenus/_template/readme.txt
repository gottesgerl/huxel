Use these two files to create scripted marking menus for a certain nodetype.

The *.json-file descripes the appeareance of the radial menu
while the *.py-file can contain modules to be called by this radial menu

(1) Copy both *.json- and *.py-file into the folder:
	{huxelpath}\scripts\python\huxelradialmenus\nodegraph\{context}\{nodetype}

(2) rename both files to {nodetype}.json and {nodetype}.py

(3) The *.json-file contains entries for all eight directions
	together with some examples, e.g. how to 
		- apply a legacy preset
		- a receipe
		- run a custommodule
		- convert the node into another time
		- add a node of a specific type to its first output
		
	Edit the file to your needs.

(4) Add custom python modules to {nodetype}.py

Enjoy!
