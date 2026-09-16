import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from app.content import catalog,exercises,lesson
from rdflib import Graph
from rdflib.plugins.sparql.parser import parseQuery,parseUpdate

def validate():
    errors=[]
    entries=exercises()
    for track in catalog()['tracks']:
        for module in track['modules']:
            group=[e for e in entries.values() if e['module_id']==module['id']]
            if len(group)!=9:errors.append(module['id']+': expected 9 exercises')
            for l in module['lessons']:
                body=lesson(l['id'])['body']
                if len(body.split())<220:errors.append(l['id']+': lesson too short')
                if 'Official references' not in body:errors.append(l['id']+': missing sources')
    for eid,e in entries.items():
        if not e.get('sources') or not e.get('wrong_solutions') or len(e.get('hints',[]))!=3:
            errors.append(eid+': incomplete authoring metadata')
        if not any(f.get('public') for f in e['fixtures']):errors.append(eid+': no public fixture')
        try:
            for filename,text in e['solution'].items():
                if filename.endswith('.ttl'):Graph().parse(data=text,format='turtle')
                elif filename=='query.rq':parseQuery(text)
                elif filename=='update.rq':parseUpdate(text)
                elif filename.endswith('.py'):compile(text,filename,'exec')
            for f in e['fixtures']:
                if f['input'].get('data'):Graph().parse(data=f['input']['data'],format='turtle')
        except Exception as exc:errors.append(eid+': '+str(exc)[:200])
    report={'lessons':sum(len(m['lessons']) for t in catalog()['tracks'] for m in t['modules']),'exercises':len(entries),'errors':errors,'scope':'Structure and syntax only; runtime and editorial review are separate gates.'}
    print(json.dumps(report,indent=2))
    return bool(errors)

if __name__=='__main__':sys.exit(validate())
