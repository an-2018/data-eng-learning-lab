"""Execute reference and counterexample submissions in disposable Docker sandboxes."""
import argparse,json,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from app.content import exercises
from app.sandbox import execute
from app.grading import compare

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runner',choices=['rdf','sparql','shacl','owl','ingestion','spark'])
    parser.add_argument('--exercise')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--counterexamples',action='store_true')
    args=parser.parse_args()
    selected=[e for e in exercises().values() if (not args.runner or e['runner']==args.runner) and (not args.exercise or e['id']==args.exercise)]
    if args.limit:selected=selected[:args.limit]
    results=[]
    for e in selected:
        started=time.monotonic();failures=[]
        for f in e['fixtures']:
            try:
                actual=execute(e['runner'],e['solution'],f['input'],e['execution'],str(uuid.uuid4()))
                if not compare(actual,f['expected'],e['grading']):
                    failures.append({'fixture':f['name'],'actual':actual,'expected':f['expected']})
            except Exception as exc:failures.append({'fixture':f['name'],'error':type(exc).__name__+': '+str(exc)})
        if args.counterexamples and not failures:
            for wrong in e['wrong_solutions']:
                rejected=False
                for f in e['fixtures']:
                    try:
                        actual=execute(e['runner'],wrong,f['input'],e['execution'],str(uuid.uuid4()))
                        if not compare(actual,f['expected'],e['grading']):rejected=True;break
                    except Exception:rejected=True;break
                if not rejected:failures.append({'error':'A known incorrect solution passed all fixtures'})
        row={'exercise':e['id'],'runner':e['runner'],'seconds':round(time.monotonic()-started,2),'passed':not failures,'failures':failures}
        results.append(row);print(json.dumps(row),flush=True)
    out=Path('.artifacts');out.mkdir(exist_ok=True)
    (out/f'runtime-audit-{args.runner or args.exercise or "all"}.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return int(any(not r['passed'] for r in results))
if __name__=='__main__':sys.exit(main())
