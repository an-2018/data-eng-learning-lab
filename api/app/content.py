import hashlib
import json
from functools import lru_cache
from pathlib import Path
import yaml
from .config import CONTENT_ROOT

@lru_cache
def catalog():
    return yaml.safe_load((CONTENT_ROOT / 'catalog.yaml').read_text(encoding='utf-8'))

@lru_cache
def exercises():
    return {p.parent.name: yaml.safe_load(p.read_text(encoding='utf-8')) for p in (CONTENT_ROOT / 'exercises').glob('*/manifest.yaml')}

def exercise(eid):
    item = exercises().get(eid)
    if not item:
        raise KeyError(eid)
    return item

def public_exercise(eid):
    item = exercise(eid)
    allowed = ['id','title','module_id','version','difficulty','mode','runner','minutes','objectives','prerequisites','statement','requirements','starter','sources','hints','variant_group','rubric','questions','status']
    out = {k: item[k] for k in allowed if k in item}
    out['questions'] = [{k:v for k,v in q.items() if k != 'answer'} for q in out.get('questions', [])]
    out['fixtures'] = [{'name': f['name'], 'data': f.get('data',''), 'format': f.get('format','turtle')} for f in item.get('fixtures',[]) if f.get('public')]
    return out

def fingerprint(item):
    return hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()

def lesson(lid):
    for track in catalog()['tracks']:
        for module in track.get('modules', []):
            for item in module.get('lessons', []):
                if item['id'] == lid:
                    return {**item, 'module_id': module['id'], 'body': (CONTENT_ROOT / 'lessons' / (lid + '.md')).read_text(encoding='utf-8'), 'sources': module['sources']}
    raise KeyError(lid)
