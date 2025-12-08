import shutil
import os
print(f"PATH: {os.environ['PATH']}")
print(f"dot path: {shutil.which('dot')}")

import graphviz
try:
    g = graphviz.Digraph()
    g.node('A')
    print("Graphviz pipe success")
    g.pipe(format='png')
except Exception as e:
    print(f"Graphviz error: {e}")
