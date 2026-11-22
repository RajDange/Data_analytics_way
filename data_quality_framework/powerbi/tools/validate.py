import json, glob, os, sys
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
BASE="/tmp/jsch"
URL="https://developer.microsoft.com/json-schemas/"
def retrieve(uri):
    p=os.path.join(BASE, uri.replace(URL,""))
    return Resource.from_contents(json.load(open(p)), default_specification=DRAFT7)
reg=Registry(retrieve=retrieve)
root=sys.argv[1]; bad=0; n=0
files=glob.glob(root+"/**/*.json",recursive=True)+glob.glob(root+"/**/*.pbir",recursive=True)
for f in files:
    doc=json.load(open(f)); sch=doc.get("$schema")
    if not sch or not sch.startswith(URL+"fabric/item"): continue
    n+=1
    schema=retrieve(sch).contents
    v=Draft7Validator(schema, registry=reg)
    errs=list(v.iter_errors(doc))
    for e in errs[:3]:
        bad+=1; print("ERR", f.replace(root,""), list(e.absolute_path), e.message[:200])
print(f"validated {n} files, {bad} errors")
