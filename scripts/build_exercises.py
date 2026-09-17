"""Compile exercise packages with private contracts and deterministic alternate fixtures."""
from pathlib import Path
import json
import yaml
from rdflib import Graph,Dataset
from build_content import ROOT,PREFIX,QP,MODULES,SOURCES,write

WORKFORCE='''ex:ava a ex:Person ; ex:name "Ava" ; ex:worksFor ex:northstar ; ex:email "ava@work.example" ; ex:years 4 ; ex:reportsTo ex:ben ; ex:employeeId "E-001" .
ex:ben a ex:Person ; ex:name "Ben" ; ex:worksFor ex:northstar ; ex:years 2 ; ex:reportsTo ex:cyra ; ex:employeeId "E-002" .
ex:cyra a ex:Person ; ex:name "Cyra" ; ex:worksFor ex:orbit ; ex:contractsFor ex:northstar ; ex:email "cyra@work.example" ; ex:years 7 .
ex:dev a ex:Person ; ex:name "Dev" ; ex:worksFor ex:orbit ; ex:contractsFor ex:orbit ; ex:years 1 .
ex:northstar a ex:Company ; ex:name "Northstar" .
ex:orbit a ex:Company ; ex:name "Orbit" .
ex:atlas a ex:Project ; ex:client ex:acme ; ex:name "Atlas" .
ex:beacon a ex:Project ; ex:client ex:delta ; ex:name "Beacon" .
ex:a1 a ex:Assignment ; ex:person ex:ava ; ex:project ex:atlas ; ex:role "Engineer" .
ex:a2 a ex:Assignment ; ex:person ex:ava ; ex:project ex:beacon ; ex:role "Reviewer" .
ex:a3 a ex:Assignment ; ex:person ex:ben ; ex:project ex:atlas ; ex:role "Engineer" .'''
ALT=WORKFORCE.replace('ex:ava','ex:ella').replace('"Ava"','"Ella"').replace('ex:ben','ex:farid').replace('"Ben"','"Farid"')+'\nex:guest a ex:Person ; ex:name "Guest" ; ex:years 4 .'

def query_result(query,data,graphs=None):
    ds=Dataset(default_union=False)
    ds.default_context.parse(data=PREFIX+data,format='turtle')
    for uri,text in (graphs or {}).items():ds.graph(uri).parse(data=text,format='turtle')
    result=ds.query(QP+query)
    if result.type=='CONSTRUCT':return {'graph':result.graph.serialize(format='turtle')}
    return json.loads(result.serialize(format='json'))

def base(mid,i,title,runner,statement,solution,fixtures,execution,grading,hint):
    source_keys=next(m[3] for m in MODULES if m[0]==mid)
    eid=f'{mid}-e{i:02d}'
    mode='guided' if i<=2 else 'assessment' if i==9 else 'practice'
    filename='query.rq' if runner=='sparql' else 'shapes.ttl' if runner=='shacl' else 'main.py' if runner=='spark' else 'update.rq' if runner=='ingestion' else 'ontology.ttl'
    starter=QP+'\n# Write a complete query here.\n' if filename.endswith('.rq') else '# Assign the output DataFrame to result.\n' if filename.endswith('.py') else PREFIX+'\n# Write your model here.\n'
    questions=[]
    if i==9:
        questions=[{'id':'meaning','prompt':'What does a passing executable check establish?','options':['The stated behavior holds on the tested fixtures.','Every possible model is correct.','The ontology is complete for the entire world.'],'answer':'The stated behavior holds on the tested fixtures.'},
          {'id':'evidence','prompt':'How should an infrastructure error affect mastery?','options':['It should count as a wrong answer.','It should not change mastery.','It should count as a pass.'],'answer':'It should not change mastery.'}]
    obj={'id':eid,'title':title,'module_id':mid,'version':'1.0.0','dataset_version':'1','grader_version':'1','runtime_version':'1',
      'difficulty':'Fundamentals' if int(mid[1:])<=4 else 'Advanced' if int(mid[1:])>=13 else 'Intermediate','mode':mode,'runner':runner,
      'minutes':12 if i<=2 else 20 if i==9 else 15,'objectives':[statement.split('\n')[0]],'prerequisites':[] if i<=2 else [f'{mid}-e01'],
      'statement':statement,'requirements':['Implement the behavior described above for every fixture.','Use the exact output variable names or file contract shown in the task.','Preserve identity, datatypes, and duplicate rows unless the task explicitly requests a change.'],
      'starter':{filename:starter},'solution':{filename:solution},'explanation':hint,
      'hints':['Start with the entity or output grain requested by the question.',hint,'Use the public dataset to trace one result from its inputs. Then consider missing values and repeated matches.'],
      'sources':[SOURCES[k] for k in source_keys],'source_review_date':'2026-09-15','status':'ready','review_status':'authored_pending_runtime_audit',
      'fixtures':fixtures,'execution':execution,'grading':grading,'questions':questions,
      'wrong_solutions':[{filename:QP+'SELECT ?wrong WHERE { FILTER(false) }' if runner in ['sparql','ingestion'] else 'result = people.limit(0)' if runner=='spark' else PREFIX}],
      'variant_group':mid,'rubric':['All stated executable requirements pass.','Explain why the implementation has the intended meaning.']}
    write(ROOT/'exercises'/eid/'manifest.yaml',yaml.safe_dump(obj,sort_keys=False,allow_unicode=True))

QUERY_SPECS={
'o03':[
 ('Find the people at Northstar','Return ?person for each Person with worksFor Northstar.','SELECT ?person WHERE { ?person a ex:Person ; ex:worksFor ex:northstar }'),
 ('Follow a project assignment','Return ?person and ?project for assignments to projects with client Acme. Preserve multiple assignments.','SELECT ?person ?project WHERE { ?a ex:person ?person ; ex:project ?project . ?project ex:client ex:acme }'),
 ('Select names, not identifiers','Return ?name for each Person. Do not return company or project names.','SELECT ?name WHERE { ?p a ex:Person ; ex:name ?name }'),
 ('Filter numeric experience','Return ?person and ?years for people with at least 3 years.','SELECT ?person ?years WHERE { ?person a ex:Person ; ex:years ?years FILTER(?years >= 3) }'),
 ('Calculate next year','Return ?person and ?nextYear, computed as years plus 1, for each Person with years.','SELECT ?person ?nextYear WHERE { ?person a ex:Person ; ex:years ?years BIND(?years+1 AS ?nextYear) }'),
 ('Constrain the employer set','Return ?person and ?company for worksFor links to Northstar or Orbit.','SELECT ?person ?company WHERE { VALUES ?company { ex:northstar ex:orbit } ?person ex:worksFor ?company }'),
 ('Connect employer names','Return ?person and ?companyName by joining worksFor to the company name.','SELECT ?person ?companyName WHERE { ?person ex:worksFor ?company . ?company ex:name ?companyName }'),
 ('Filter an assignment role','Return ?person for each assignment whose role is the string Engineer.','SELECT ?person WHERE { ?a ex:person ?person ; ex:role "Engineer" }'),
 ('Checkpoint: client staffing','Return distinct ?name values for people assigned to projects for Acme.','SELECT DISTINCT ?name WHERE { ?a ex:person ?p ; ex:project ?pr . ?pr ex:client ex:acme . ?p ex:name ?name }')],
'o04':[
 ('Keep people without email','Return ?person and optional ?email for every Person, retaining people without email.','SELECT ?person ?email WHERE { ?person a ex:Person OPTIONAL { ?person ex:email ?email } }'),
 ('Combine employees and contractors','Return ?person for worksFor Northstar OR contractsFor Northstar. Preserve branch duplicates.','SELECT ?person WHERE { { ?person ex:worksFor ex:northstar } UNION { ?person ex:contractsFor ex:northstar } }'),
 ('Find missing contact details','Return ?person for each Person without a recorded email in this dataset.','SELECT ?person WHERE { ?person a ex:Person FILTER NOT EXISTS { ?person ex:email ?e } }'),
 ('Select people with assignments','Return ?person once for each Person having at least one assignment. Use existence rather than multiplying rows.','SELECT ?person WHERE { ?person a ex:Person FILTER EXISTS { ?a ex:person ?person } }'),
 ('Preserve a filtered optional','Return every ?person and optional ?email only when that email contains work.example.','SELECT ?person ?email WHERE { ?person a ex:Person OPTIONAL { ?person ex:email ?email FILTER(CONTAINS(STR(?email),"work.example")) } }'),
 ('Deduplicate contributing people','Return DISTINCT ?person values found on assignments.','SELECT DISTINCT ?person WHERE { ?a ex:person ?person }'),
 ('Exclude known employees','Return ?person for all Person instances except those with worksFor Northstar.','SELECT ?person WHERE { ?person a ex:Person MINUS { ?person ex:worksFor ex:northstar } }'),
 ('Optional display fallback','Return ?person and ?contact. Use the email if present, otherwise the string missing.','SELECT ?person (COALESCE(?email,"missing") AS ?contact) WHERE { ?person a ex:Person OPTIONAL { ?person ex:email ?email } }'),
 ('Checkpoint: alternative employers','Return ?person for worksFor Orbit OR contractsFor Orbit. Keep duplicate matches from both alternatives.','SELECT ?person WHERE { { ?person ex:worksFor ex:orbit } UNION { ?person ex:contractsFor ex:orbit } }')],
'o05':[
 ('Count employees by company','Return ?company and ?people, the count of distinct worksFor subjects per company.','SELECT ?company (COUNT(DISTINCT ?p) AS ?people) WHERE { ?p ex:worksFor ?company } GROUP BY ?company'),
 ('Traverse a reporting chain','Return ?person and ?manager for each one-or-more-step reportsTo path.','SELECT ?person ?manager WHERE { ?person ex:reportsTo+ ?manager }'),
 ('Count assignments at their grain','Return ?person and ?assignments, counting assignment resources per person.','SELECT ?person (COUNT(?a) AS ?assignments) WHERE { ?a ex:person ?person } GROUP BY ?person'),
 ('Filter aggregate groups','Return ?person with at least two assignments. Return no count column.','SELECT ?person WHERE { ?a ex:person ?person } GROUP BY ?person HAVING(COUNT(?a)>=2)'),
 ('Use a subquery result','Return ?name and ?assignments by joining person names to a subquery that counts their assignments.','SELECT ?name ?assignments WHERE { { SELECT ?p (COUNT(?a) AS ?assignments) WHERE { ?a ex:person ?p } GROUP BY ?p } ?p ex:name ?name }'),
 ('Ask about a client','Return an ASK boolean indicating whether Acme is the client of a project.','ASK { ?project ex:client ex:acme }'),
 ('Construct employer relationships','Construct a graph replacing each worksFor predicate with employer.','CONSTRUCT { ?p ex:employer ?c } WHERE { ?p ex:worksFor ?c }'),
 ('Choose a named snapshot','Return ?person and ?company from worksFor triples in GRAPH ex:snapshot only.','SELECT ?person ?company WHERE { GRAPH ex:snapshot { ?person ex:worksFor ?company } }'),
 ('Checkpoint: unique client contributors','Return ?client and ?people, counting distinct people assigned to that client projects.','SELECT ?client (COUNT(DISTINCT ?person) AS ?people) WHERE { ?a ex:person ?person ; ex:project ?p . ?p ex:client ?client } GROUP BY ?client')],
'o15':[
 ('Anchor a selective lookup','Return ?person and ?company for employeeId E-001 and their worksFor relationship.','SELECT ?person ?company WHERE { ?person ex:employeeId "E-001" ; ex:worksFor ?company }'),
 ('Repair the disconnected join','Return ?person and ?companyName using a shared company variable, without a Cartesian product.','SELECT ?person ?companyName WHERE { ?person ex:worksFor ?company . ?company ex:name ?companyName }'),
 ('Avoid counting the label join','Return ?company and ?people counting distinct employees without joining all graph labels.','SELECT ?company (COUNT(DISTINCT ?p) AS ?people) WHERE { ?p ex:worksFor ?company } GROUP BY ?company'),
 ('Scope the graph first','Return ?person from worksFor Northstar inside GRAPH ex:snapshot.','SELECT ?person WHERE { GRAPH ex:snapshot { ?person ex:worksFor ex:northstar } }'),
 ('Preserve optional semantics','Return every ?person and optional ?email; tune without dropping people missing email.','SELECT ?person ?email WHERE { ?person a ex:Person OPTIONAL { ?person ex:email ?email } }'),
 ('Bind a path endpoint','Return ?person who reaches Cyra through one or more reportsTo edges.','SELECT ?person WHERE { ?person ex:reportsTo+ ex:cyra }'),
 ('Project only requested values','Return distinct ?company resources with employees; omit names and employees.','SELECT DISTINCT ?company WHERE { ?p ex:worksFor ?company }'),
 ('Bound an intermediate group','Return ?person with at least two assignments using the correct grouping grain.','SELECT ?person WHERE { ?a ex:person ?person } GROUP BY ?person HAVING(COUNT(?a)>=2)'),
 ('Checkpoint: equivalent result contract','Return ?client and ?people, distinct contributor counts. Optimization must preserve these values.','SELECT ?client (COUNT(DISTINCT ?p) AS ?people) WHERE { ?a ex:person ?p ; ex:project ?pr . ?pr ex:client ?client } GROUP BY ?client')],
'o17':[
 ('Anchor an identifier lookup','Return person and company for employeeId E-001.','SELECT ?person ?company WHERE { ?person ex:employeeId "E-001" ; ex:worksFor ?company }'),
 ('Repair a disconnected join','Return person and company name through a shared company variable.','SELECT ?person ?companyName WHERE { ?person ex:worksFor ?company . ?company ex:name ?companyName }'),
 ('Scope a snapshot','Return people at Northstar only from GRAPH ex:snapshot.','SELECT ?person WHERE { GRAPH ex:snapshot { ?person ex:worksFor ex:northstar } }'),
 ('Bind a path endpoint','Return people who reach Cyra through reportsTo.','SELECT ?person WHERE { ?person ex:reportsTo+ ex:cyra }'),
 ('Count at employee grain','Return company and distinct employee count.','SELECT ?company (COUNT(DISTINCT ?p) AS ?people) WHERE { ?p ex:worksFor ?company } GROUP BY ?company'),
 ('Keep optional semantics','Return each person and optional email.','SELECT ?person ?email WHERE { ?person a ex:Person OPTIONAL { ?person ex:email ?email } }'),
 ('Avoid surplus projection','Return distinct companies with employees.','SELECT DISTINCT ?company WHERE { ?p ex:worksFor ?company }'),
 ('Bound an aggregate','Return people with two or more assignments.','SELECT ?person WHERE { ?a ex:person ?person } GROUP BY ?person HAVING(COUNT(?a)>=2)'),
 ('Checkpoint: preserve result semantics','Return client and distinct contributor count.','SELECT ?client (COUNT(DISTINCT ?p) AS ?people) WHERE { ?a ex:person ?p ; ex:project ?project . ?project ex:client ?client } GROUP BY ?client')],
'o18':[
 ('Query one source graph','Return people in the snapshot graph.','SELECT ?person WHERE { GRAPH ex:snapshot { ?person a ex:Person } }'),
 ('Scope an employer lookup','Return snapshot people working for Northstar.','SELECT ?person WHERE { GRAPH ex:snapshot { ?person ex:worksFor ex:northstar } }'),
 ('Find source labels','Return resources and labels from the source graph.','SELECT ?resource ?label WHERE { GRAPH ex:snapshot { ?resource ex:name ?label } }'),
 ('Count a source graph','Return number of people in the snapshot.','SELECT (COUNT(?person) AS ?people) WHERE { GRAPH ex:snapshot { ?person a ex:Person } }'),
 ('Compare graph boundaries','Return companies referenced within snapshot.','SELECT DISTINCT ?company WHERE { GRAPH ex:snapshot { ?person ex:worksFor ?company } }'),
 ('Retain source context','Return person and company from snapshot.','SELECT ?person ?company WHERE { GRAPH ex:snapshot { ?person ex:worksFor ?company } }'),
 ('Constrain graph search','Return the named Atlas project from snapshot.','SELECT ?project WHERE { GRAPH ex:snapshot { ?project ex:client ex:acme } }'),
 ('Discover reusable labels','Return name labels for companies.','SELECT ?company ?name WHERE { GRAPH ex:snapshot { ?company a ex:Company ; ex:name ?name } }'),
 ('Checkpoint: source-scoped contributors','Return snapshot people assigned to Acme projects.','SELECT ?person WHERE { GRAPH ex:snapshot { ?a ex:person ?person ; ex:project ?project . ?project ex:client ex:acme } }')],
}
QUERY_SPECS['o19']=QUERY_SPECS['o17']
QUERY_SPECS['o20']=QUERY_SPECS['o18']

def build_queries():
    for mid,specs in QUERY_SPECS.items():
        for i,(title,statement,query) in enumerate(specs,1):
            fixtures=[]
            for j,data in enumerate([WORKFORCE,ALT,WORKFORCE+'\nex:ava ex:contractsFor ex:northstar .\nex:visitor a ex:Person ; ex:email "visitor@personal.example" .']):
                graphs={'https://example.org/snapshot':PREFIX+data}
                fixtures.append({'name':'Workforce sample' if j==0 else 'Alternate workforce','public':j==0,'data':PREFIX+data,'format':'turtle','input':{'data':PREFIX+data,'graphs':graphs},'expected':query_result(query,data,graphs),'feedback':'Check the join variables, missing values, projected columns, and duplicate counts.'})
            base(mid,i,title,'sparql',statement+'\n\nThe dataset contains Person, Company, Project, and Assignment resources. All example IRIs use https://example.org/.',QP+query,fixtures,{}, {'kind':'graph' if query.startswith('CONSTRUCT') else 'sparql'},'Trace the shared variables between triple patterns. Use the exact output names requested and preserve the stated result grain.')

RDF_SPECS={
'o01':[
('Describe a person','ex:ava a ex:Person .','Create exactly one type triple: Ava is a Person.'),
('Link an employer','ex:ava ex:worksFor ex:northstar .','Link Ava to Northstar with worksFor. Both endpoints must be resources.'),
('Give a resource a name','ex:ava ex:name "Ava" .','Give Ava the string name Ava.'),
('Encode an integer','ex:ava ex:years "4"^^xsd:integer .','Give Ava years with the typed integer literal 4.'),
('Add a language-tagged label','ex:Person rdfs:label "Pessoa"@pt .','Label the Person class Pessoa in Portuguese.'),
('Model a local address','ex:ava ex:address [ ex:city "Porto" ] .','Link Ava to an anonymous address with city Porto.'),
('Write multiple values','ex:ava ex:skill ex:Python, ex:SPARQL .','Give Ava two resource-valued skills, Python and SPARQL.'),
('Type a calendar date','ex:ava ex:joined "2024-01-15"^^xsd:date .','Give Ava the joined date 2024-01-15 using xsd:date.'),
('Checkpoint: connected facts','ex:ava a ex:Person ; ex:worksFor ex:northstar . ex:northstar ex:name "Northstar" .','Create exactly the three facts: Ava is a Person, Ava worksFor Northstar, and Northstar has name Northstar.')],
'o06':[
('Give an assignment identity','ex:a1 a ex:Assignment ; ex:person ex:ava ; ex:project ex:atlas .','Create a1 as an Assignment linking Ava and Atlas.'),
('Put role on the relationship','ex:a1 a ex:Assignment ; ex:person ex:ava ; ex:project ex:atlas ; ex:role "Reviewer" .','Model Ava reviewing Atlas using Assignment a1 and role Reviewer.'),
('Model an order line','ex:line1 a ex:OrderLine ; ex:order ex:order1 ; ex:product ex:tool ; ex:quantity 2 .','Create line1 with type OrderLine, order order1, product tool, and integer quantity 2.'),
('Reuse a brand resource','ex:tool ex:brand ex:forge . ex:forge a ex:Brand ; ex:name "Forge" .','Link tool to Brand forge, whose name is Forge.'),
('Separate two assignments','ex:a1 ex:person ex:ava ; ex:project ex:atlas ; ex:role "Engineer" . ex:a2 ex:person ex:ava ; ex:project ex:beacon ; ex:role "Reviewer" .','Represent Ava on Atlas as Engineer via a1 and on Beacon as Reviewer via a2. Include only the six stated relationships.'),
('Record a decimal allocation','ex:a1 ex:allocation "0.5"^^xsd:decimal .','Record decimal allocation 0.5 on Assignment a1.'),
('Preserve a lifecycle attribute','ex:order1 a ex:Order ; ex:status "shipped" .','Represent order1 as an Order with status shipped.'),
('Preserve independent product identity','ex:line1 ex:product ex:tool . ex:line2 ex:product ex:tool .','Link two separate lines, line1 and line2, to the same tool product.'),
('Checkpoint: priced association','ex:line1 a ex:OrderLine ; ex:order ex:order1 ; ex:product ex:tool ; ex:quantity 2 ; ex:unitPrice "12.50"^^xsd:decimal .','Model line1 as an OrderLine for order1 and tool, quantity 2, and decimal unitPrice 12.50.')],
'o11':[
('Create a SKOS concept','ex:Tools a <http://www.w3.org/2004/02/skos/core#Concept> .','Type Tools as a SKOS Concept.'),
('Use a preferred label','ex:Tools <http://www.w3.org/2004/02/skos/core#prefLabel> "Tools"@en .','Give Tools the SKOS English preferred label Tools.'),
('Assign a concept scheme','ex:Tools <http://www.w3.org/2004/02/skos/core#inScheme> ex:Catalog .','Place Tools in concept scheme Catalog using SKOS inScheme.'),
('Model a broader category','ex:HandTools <http://www.w3.org/2004/02/skos/core#broader> ex:Tools .','State that HandTools has the broader SKOS concept Tools.'),
('Keep a mapping appropriately weak','ex:SourceTools <http://www.w3.org/2004/02/skos/core#closeMatch> ex:Tools .','Use SKOS closeMatch from SourceTools to Tools; do not assert OWL identity.'),
('Deprecate a term','ex:LegacyEmployee owl:deprecated true .','Mark LegacyEmployee deprecated using owl:deprecated and a boolean true.'),
('Identify a version','ex:Workforce a owl:Ontology ; owl:versionIRI ex:WorkforceV2 .','Declare Workforce an ontology with version IRI WorkforceV2.'),
('Add multilingual labels','ex:Tools <http://www.w3.org/2004/02/skos/core#prefLabel> "Tools"@en, "Ferramentas"@pt .','Give Tools preferred labels Tools in English and Ferramentas in Portuguese.'),
('Checkpoint: reusable category','ex:Tools a <http://www.w3.org/2004/02/skos/core#Concept> ; <http://www.w3.org/2004/02/skos/core#inScheme> ex:Catalog ; <http://www.w3.org/2004/02/skos/core#prefLabel> "Tools"@en .','Create Tools as a SKOS Concept in Catalog with English preferred label Tools.')],
'o12':[
('Preserve the raw value','ex:record1 ex:rawEmail " Ava@Example.org " ; ex:comparisonEmail "Ava@example.org" .','Retain rawEmail with its original spaces and casing and store comparisonEmail Ava@example.org separately.'),
('Record a deterministic match','ex:match1 ex:left ex:recordA ; ex:right ex:recordB ; ex:rule "company+employeeId" .','Describe match1 between recordA and recordB with rule company+employeeId.'),
('Route uncertain evidence','ex:match1 ex:score "0.82"^^xsd:decimal ; ex:decision "review" .','Record score 0.82 and decision review on match1.'),
('Preserve both source records','ex:ava <http://www.w3.org/ns/prov#wasDerivedFrom> ex:recordA, ex:recordB .','Link canonical Ava to both recordA and recordB with PROV wasDerivedFrom.'),
('Record a rule version','ex:match1 ex:ruleVersion "2.1" ; ex:reviewer ex:analyst .','Record ruleVersion 2.1 and reviewer analyst for match1.'),
('Reject conflicting evidence','ex:match1 ex:decision "reject" ; ex:reason "conflicting employee identifiers" .','Record a rejected match with the exact reason conflicting employee identifiers.'),
('Keep a scoped identifier','ex:record1 ex:employeeId "42" ; ex:company ex:northstar .','Preserve string employeeId 42 and company Northstar on record1.'),
('Link the mapping activity','ex:ava <http://www.w3.org/ns/prov#wasGeneratedBy> ex:mapping42 .','Record mapping42 as the activity generating canonical Ava using PROV.'),
('Checkpoint: reversible decision','ex:match1 ex:left ex:recordA ; ex:right ex:recordB ; ex:decision "review" ; ex:ruleVersion "2.1" .','Create match1 linking recordA and recordB, decision review, ruleVersion 2.1. Do not assert sameAs.')],
'o16':[
('Link releases','ex:release2 ex:replaces ex:release1 .','State that release2 replaces release1.'),
('Retain migration provenance','ex:snapshot2 <http://www.w3.org/ns/prov#wasDerivedFrom> ex:snapshot1 .','Use PROV to link snapshot2 to its source snapshot1.'),
('Record validation evidence','ex:release2 ex:validationReport ex:report42 .','Link release2 to validationReport report42.'),
('Identify the release reviewer','ex:release2 ex:approvedBy ex:reviewer .','Record reviewer as the approving resource for release2.'),
('Record an observed violation count','ex:report42 ex:violations 0 ; ex:focusNodes 120 .','Record integer violations 0 and focusNodes 120 so that empty validation is distinguishable.'),
('Record a rollback target','ex:release2 ex:rollbackTarget ex:snapshot1 .','Link release2 to rollbackTarget snapshot1.'),
('Record the mapping version','ex:release2 ex:mappingVersion "2.1" .','Record mappingVersion 2.1 as a string on release2.'),
('Mark a deprecated predicate','ex:oldName owl:deprecated true ; rdfs:comment "Use name for new data." .','Deprecate oldName and attach the exact comment Use name for new data.'),
('Checkpoint: traceable release','ex:release2 ex:replaces ex:release1 ; ex:validationReport ex:report42 ; ex:approvedBy ex:reviewer ; ex:rollbackTarget ex:snapshot1 .','Record release2 replacing release1 with report42, reviewer, and rollback snapshot1 using the predicates from this module.')],
}

def build_rdf():
    for mid,specs in RDF_SPECS.items():
        for i,(title,solution,statement) in enumerate(specs,1):
            fixtures=[{'name':'Required graph','public':True,'data':'No initial triples. Create the stated graph.','input':{'data':''},'expected':{'graph':PREFIX+solution},'feedback':'Compare resource versus literal values, datatypes, predicates, and the exact set of required triples.'}]
            base(mid,i,title,'rdf',statement+'\n\nCreate exactly the stated facts, with no extra triples. Blank-node labels may differ. In open-ended projects, additional modeling choices are assessed separately by rubric.',PREFIX+solution,fixtures,{'query':'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }'},{'kind':'graph'},'Use resource IRIs for entities and typed literals for scalar values. The graph is compared structurally, not as Turtle text.')

def build_rdfs():
    specs=[
      ('Infer a superclass','ex:Engineer rdfs:subClassOf ex:Person .','ex:ava a ex:Engineer .','ASK { ex:ava a ex:Person }','Make Engineer a subclass of Person.'),
      ('Infer an endpoint type','ex:worksFor rdfs:domain ex:Person .','ex:ava ex:worksFor ex:northstar .','ASK { ex:ava a ex:Person }','Give worksFor domain Person.'),
      ('Infer a company type','ex:worksFor rdfs:range ex:Company .','ex:ava ex:worksFor ex:northstar .','ASK { ex:northstar a ex:Company }','Give worksFor range Company.'),
      ('Generalize a property','ex:managesProject rdfs:subPropertyOf ex:contributesTo .','ex:ava ex:managesProject ex:atlas .','ASK { ex:ava ex:contributesTo ex:atlas }','Make managesProject a subproperty of contributesTo.'),
      ('Chain a class hierarchy','ex:SeniorEngineer rdfs:subClassOf ex:Engineer . ex:Engineer rdfs:subClassOf ex:Person .','ex:ava a ex:SeniorEngineer .','ASK { ex:ava a ex:Person }','Build SeniorEngineer → Engineer → Person subclass relationships.'),
      ('Apply both domains','ex:worksFor rdfs:domain ex:Person, ex:Agent .','ex:ava ex:worksFor ex:northstar .','ASK { ex:ava a ex:Person, ex:Agent }','Declare both Person and Agent as domains of worksFor. Observe conjunction.'),
      ('Type assignment endpoints','ex:person rdfs:range ex:Person . ex:project rdfs:range ex:Project .','ex:a1 ex:person ex:ava ; ex:project ex:atlas .','ASK { ex:ava a ex:Person . ex:atlas a ex:Project }','Give person range Person and project range Project.'),
      ('Compose property implication','ex:leads rdfs:subPropertyOf ex:managesProject . ex:managesProject rdfs:subPropertyOf ex:contributesTo .','ex:ava ex:leads ex:atlas .','ASK { ex:ava ex:contributesTo ex:atlas }','Build leads → managesProject → contributesTo subproperty links.'),
      ('Checkpoint: inference is not validation','ex:worksFor rdfs:domain ex:Person ; rdfs:range ex:Company .','ex:atlas ex:worksFor ex:northstar .','ASK { ex:atlas a ex:Person . ex:northstar a ex:Company }','Declare domain Person and range Company for worksFor, then observe that Atlas is inferred a Person.')]
    for i,(title,sol,data,q,statement) in enumerate(specs,1):
        fixtures=[{'name':'Inference sample','public':True,'data':PREFIX+data,'input':{'data':PREFIX+data},'expected':{'boolean':True},'feedback':'Check the direction of the subclass/subproperty or endpoint declaration.'}]
        base('o02',i,title,'rdf',statement+'\n\nDo not assert the inferred facts directly: supply vocabulary declarations. RDFS inference is enabled.',PREFIX+sol,fixtures,{'query':QP+q,'inference':'rdfs'},{'kind':'sparql'},'Domain and range infer endpoint types. Subclass and subproperty implications only run from specialized to general.')

SHAPES=[
('o09','Select people and require an identifier','[ sh:path ex:employeeId ; sh:minCount 1 ]','ex:ava a ex:Person ; ex:employeeId "E1" .','ex:ava a ex:Person .','Require at least one employeeId for each Person.'),
('o09','Exactly one employee identifier','[ sh:path ex:employeeId ; sh:minCount 1 ; sh:maxCount 1 ]','ex:ava a ex:Person ; ex:employeeId "E1" .','ex:ava a ex:Person ; ex:employeeId "E1", "E2" .','Require exactly one employeeId for each Person.'),
('o09','Require a string identifier','[ sh:path ex:employeeId ; sh:datatype xsd:string ]','ex:ava a ex:Person ; ex:employeeId "E1" .','ex:ava a ex:Person ; ex:employeeId 1 .','Require every employeeId value to have datatype xsd:string; absence is allowed.'),
('o09','Require Company-valued employers','[ sh:path ex:worksFor ; sh:class ex:Company ]','ex:ava a ex:Person ; ex:worksFor ex:northstar . ex:northstar a ex:Company .','ex:ava a ex:Person ; ex:worksFor "Northstar" .','Require every worksFor value of a Person to be a Company instance.'),
('o09','Limit optional email','[ sh:path ex:email ; sh:maxCount 1 ]','ex:ava a ex:Person .','ex:ava a ex:Person ; ex:email "a@x", "b@x" .','Allow zero or one email per Person.'),
('o09','Require integer experience','[ sh:path ex:years ; sh:datatype xsd:integer ]','ex:ava a ex:Person ; ex:years 4 .','ex:ava a ex:Person ; ex:years "four" .','Require years values to be integers.'),
('o09','Validate a required employer','[ sh:path ex:worksFor ; sh:minCount 1 ; sh:class ex:Company ]','ex:ava a ex:Person ; ex:worksFor ex:northstar . ex:northstar a ex:Company .','ex:ava a ex:Person .','Require at least one Company-valued worksFor value for each Person.'),
('o09','Reject negative experience','[ sh:path ex:years ; sh:minInclusive 0 ]','ex:ava a ex:Person ; ex:years 0 .','ex:ava a ex:Person ; ex:years -1 .','Require every years value to be at least zero.'),
('o09','Checkpoint: employee contract','[ sh:path ex:employeeId ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ], [ sh:path ex:worksFor ; sh:minCount 1 ; sh:class ex:Company ]','ex:ava a ex:Person ; ex:employeeId "E1" ; ex:worksFor ex:northstar . ex:northstar a ex:Company .','ex:ava a ex:Person ; ex:employeeId 1 ; ex:worksFor "Northstar" .','Require exactly one string employeeId and at least one Company-valued worksFor.'),
('o10','Restrict an allowed value set','[ sh:path ex:status ; sh:in ( "active" "inactive" ) ]','ex:ava a ex:Person ; ex:status "active" .','ex:ava a ex:Person ; ex:status "unknown" .','Allow only active or inactive string status values.'),
('o10','Validate a nested address','[ sh:path ex:address ; sh:node [ sh:property [ sh:path ex:city ; sh:minCount 1 ] ] ]','ex:ava a ex:Person ; ex:address [ ex:city "Porto" ] .','ex:ava a ex:Person ; ex:address [ ex:country "PT" ] .','When an address exists, require it to have at least one city.'),
('o10','Set a bounded experience range','[ sh:path ex:years ; sh:minInclusive 0 ; sh:maxInclusive 60 ]','ex:ava a ex:Person ; ex:years 30 .','ex:ava a ex:Person ; ex:years 61 .','Require each years value to be between 0 and 60 inclusive.'),
('o10','Validate an email pattern','[ sh:path ex:email ; sh:pattern "^[^@]+@[^@]+$" ]','ex:ava a ex:Person ; ex:email "a@work.example" .','ex:ava a ex:Person ; ex:email "missing-at-sign" .','Use pattern ^[^@]+@[^@]+$ for email values. This is a training rule, not full email validation.'),
('o10','Follow a sequence path','[ sh:path ( ex:address ex:city ) ; sh:minCount 1 ]','ex:ava a ex:Person ; ex:address [ ex:city "Porto" ] .','ex:ava a ex:Person .','Require at least one city reachable through address then city.'),
('o10','Require resource employers','[ sh:path ex:worksFor ; sh:nodeKind sh:IRI ]','ex:ava a ex:Person ; ex:worksFor ex:northstar .','ex:ava a ex:Person ; ex:worksFor [ ex:name "Northstar" ] .','Require worksFor values to be IRIs, excluding blank nodes and literals.'),
('o10','Compare chronological fields','[ sh:path ex:start ; sh:lessThanOrEquals ex:end ]','ex:ava a ex:Person ; ex:start 1 ; ex:end 2 .','ex:ava a ex:Person ; ex:start 3 ; ex:end 2 .','Require start values to be no greater than end values when both are present.'),
('o10','Validate a unique language','[ sh:path ex:label ; sh:uniqueLang true ]','ex:ava a ex:Person ; ex:label "Ava"@en, "Pessoa"@pt .','ex:ava a ex:Person ; ex:label "Ava"@en, "Person"@en .','Permit at most one label per language tag.'),
('o10','Checkpoint: nested required address','[ sh:path ex:address ; sh:minCount 1 ; sh:node [ sh:property [ sh:path ex:city ; sh:minCount 1 ; sh:datatype xsd:string ] ] ]','ex:ava a ex:Person ; ex:address [ ex:city "Porto" ] .','ex:ava a ex:Person ; ex:address [ ex:city 42 ] .','Require an address and require every address to have at least one string-valued city.')]

def build_shapes():
    counts={}
    for mid,title,props,good,bad,statement in SHAPES:
        counts[mid]=counts.get(mid,0)+1
        sol=PREFIX+'ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ; sh:property '+props+' .'
        fixtures=[]
        for j,(data,expected) in enumerate([(good,True),(bad,False),(good.replace('ex:ava','ex:other'),True),(bad.replace('ex:ava','ex:other'),False)]):
            fixtures.append({'name':'Valid sample' if expected else 'Invalid sample','public':j<2,'data':PREFIX+data,'input':{'data':PREFIX+data},'expected':{'conforms':expected},'feedback':'The shape must accept valid data and reject invalid data, including people with different IRIs.'})
        base(mid,counts[mid],title,'shacl',statement+'\n\nUse sh:targetClass ex:Person. Validation uses the explicit data graph with no OWL materialization.',sol,fixtures,{}, {'kind':'shacl'},'Select Person focus nodes, follow the stated property path, and constrain its value nodes. Cardinality and value type are independent requirements.')

def build_owl():
    declarations='ex:Person a owl:Class . ex:Employee a owl:Class . ex:Company a owl:Class . ex:Engineer a owl:Class . ex:Impossible a owl:Class . ex:worksFor a owl:ObjectProperty . ex:employs a owl:ObjectProperty . ex:ava a owl:NamedIndividual . ex:northstar a owl:NamedIndividual .\n'
    specs=[
     ('o07','Preserve subclass direction','ex:Employee rdfs:subClassOf ex:Person .','ex:ava a ex:Employee .',[('type','person','Person','ava',True)],'Make Employee a subclass of Person.'),
     ('o07','Define equivalent classes','ex:Employee owl:equivalentClass ex:Engineer .','ex:ava a ex:Engineer .',[('type','employee','Employee','ava',True)],'Make Employee and Engineer equivalent classes.'),
     ('o07','Keep the reverse implication absent','ex:Employee rdfs:subClassOf ex:Person .','ex:ava a ex:Person .',[('type','employee','Employee','ava',False),('subclass','hierarchy','Employee','Person',True)],'Make Employee a subclass of Person without making every Person an Employee.'),
     ('o07','State class disjointness','ex:Person owl:disjointWith ex:Company .','ex:ava a ex:Person, ex:Company .',[], 'Make Person and Company disjoint; this fixture should become inconsistent.'),
     ('o07','Classify through a sufficient condition','ex:Employee owl:equivalentClass [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:someValuesFrom ex:Company ] .','ex:ava ex:worksFor ex:northstar . ex:northstar a ex:Company .',[('type','employee','Employee','ava',True)],'Define Employee as equivalent to having some Company-valued worksFor relationship.'),
     ('o07','Use an inverse employment property','ex:worksFor owl:inverseOf ex:employs . ex:Employee owl:equivalentClass [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:someValuesFrom ex:Company ] .','ex:northstar a ex:Company ; ex:employs ex:ava .',[('type','employee','Employee','ava',True)],'Make worksFor inverse to employs and define Employee by some worksFor Company.'),
     ('o07','Leave an unrecorded fact unknown','ex:Employee rdfs:subClassOf ex:Person .','ex:ava a ex:Person .',[('type','employee','Employee','ava',False)],'Declare Employee a subclass of Person. Do not infer Employee for a Person without supporting facts.'),
     ('o07','Compose a class hierarchy','ex:Engineer rdfs:subClassOf ex:Employee . ex:Employee rdfs:subClassOf ex:Person .','ex:ava a ex:Engineer .',[('type','person','Person','ava',True),('type','employee','Employee','ava',True)],'Build Engineer → Employee → Person.'),
     ('o07','Checkpoint: necessary is not sufficient','ex:Employee rdfs:subClassOf ex:Person .','ex:ava a ex:Person .',[('subclass','required','Employee','Person',True),('subclass','reverse','Person','Employee',False)],'Ensure Employee implies Person while Person does not imply Employee.'),
     ('o08','Require an existential employer','ex:Employee rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:someValuesFrom ex:Company ] .','ex:ava a ex:Employee .',[('satisfiable','possible','Employee','',True)],'Add an existential Company employer restriction to Employee. Missing explicit employer data must remain consistent.'),
     ('o08','Constrain all recorded employers','ex:Employee rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:allValuesFrom ex:Company ] .','ex:ava a ex:Employee ; ex:worksFor ex:northstar .',[('type','company','Company','northstar',True)],'Constrain all Employee worksFor values to Company.'),
     ('o08','Diagnose an impossible class','ex:Impossible rdfs:subClassOf ex:Person, ex:Company . ex:Person owl:disjointWith ex:Company .','',[('satisfiable','possible','Impossible','',False)],'Make Impossible a subclass of disjoint Person and Company. The ontology remains consistent without instances.'),
     ('o08','Distinguish inconsistency from emptiness','ex:Impossible rdfs:subClassOf ex:Person, ex:Company . ex:Person owl:disjointWith ex:Company .','ex:ava a ex:Impossible .',[],'Use the conflicting hierarchy and observe inconsistency when Ava instantiates Impossible.'),
     ('o08','Allow an empty universal restriction','ex:Employee rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:allValuesFrom ex:Company ] .','ex:ava a ex:Employee .',[('satisfiable','possible','Employee','',True)],'Constrain all worksFor values to Company without requiring any explicit employer.'),
     ('o08','Use a value restriction','ex:Employee owl:equivalentClass [ a owl:Restriction ; owl:onProperty ex:worksFor ; owl:hasValue ex:northstar ] .','ex:ava ex:worksFor ex:northstar .',[('type','employee','Employee','ava',True)],'Define Employee as equivalent to worksFor value Northstar.'),
     ('o08','Intersect two classes','ex:Engineer owl:equivalentClass [ owl:intersectionOf ( ex:Person ex:Employee ) ] .','ex:ava a ex:Person, ex:Employee .',[('type','engineer','Engineer','ava',True)],'Define Engineer as the intersection of Person and Employee.'),
     ('o08','Union does not require both','ex:Engineer owl:equivalentClass [ owl:unionOf ( ex:Person ex:Employee ) ] .','ex:ava a ex:Person .',[('type','engineer','Engineer','ava',True)],'Define Engineer as the union of Person and Employee for this logical exercise.'),
     ('o08','Checkpoint: satisfiability contract','ex:Impossible rdfs:subClassOf ex:Person, ex:Company . ex:Person owl:disjointWith ex:Company .','',[('satisfiable','impossible','Impossible','',False),('satisfiable','person','Person','',True)],'Make Impossible unsatisfiable while keeping Person satisfiable and the ontology consistent.')]
    counts={}
    for mid,title,sol,data,checks,statement in specs:
        counts[mid]=counts.get(mid,0)+1
        expected={'consistent':False if not checks else True}
        if checks: expected['requiredAxioms']=True
        config=[]
        for kind,key,cls,value,want in checks:
            expected[key]=want
            config.append({'kind':kind,'id':key,'class':'https://example.org/'+cls,('super' if kind=='subclass' else 'individual'):'https://example.org/'+value})
        fixtures=[{'name':'Reasoning fixture','public':True,'data':PREFIX+declarations+data,'input':{'data':PREFIX+declarations+data,'checks':config,'checkAxioms':PREFIX+declarations+sol},'expected':expected,'feedback':'Check consistency first, then the direction and strength of the requested entailment.'}]
        base(mid,counts[mid],title,'owl',statement+'\n\nThe fixture supplies entity declarations. Do not replace reasoning with explicit answers. Work within OWL 2 DL.',PREFIX+declarations+sol,fixtures,{}, {'kind':'owl'},'Subclass axioms state necessary conditions. Equivalence states both directions. Missing facts and unsatisfiable classes must be distinguished from inconsistent ontologies.')

def build_ingestion():
    tasks=[
      ('Stage source facts','INSERT { GRAPH ex:staging { ?s ?p ?o } } WHERE { ?s ?p ?o }','SELECT ?s ?p ?o WHERE { GRAPH ex:staging { ?s ?p ?o } }'),
      ('Normalize source names','INSERT { GRAPH ex:staging { ?s ex:name ?name } } WHERE { ?s ex:rawName ?name }','SELECT ?s ?name WHERE { GRAPH ex:staging { ?s ex:name ?name } }'),
      ('Quarantine missing identifiers','INSERT { GRAPH ex:quarantine { ?s ex:reason "missing employeeId" } } WHERE { ?s a ex:Person FILTER NOT EXISTS { ?s ex:employeeId ?id } }','SELECT ?s ?reason WHERE { GRAPH ex:quarantine { ?s ex:reason ?reason } }'),
      ('Publish identified people','INSERT { GRAPH ex:published { ?s ex:employeeId ?id } } WHERE { ?s a ex:Person ; ex:employeeId ?id }','SELECT ?s ?id WHERE { GRAPH ex:published { ?s ex:employeeId ?id } }'),
      ('Record snapshot provenance','INSERT { GRAPH ex:provenance { ?s ex:sourceSnapshot ex:snapshot1 } } WHERE { ?s a ex:Person }','SELECT ?s ?snapshot WHERE { GRAPH ex:provenance { ?s ex:sourceSnapshot ?snapshot } }'),
      ('Replace a legacy property','DELETE { ?s ex:rawName ?name } INSERT { ?s ex:name ?name } WHERE { ?s ex:rawName ?name }','SELECT ?s ?name WHERE { ?s ex:name ?name }'),
      ('Stage and promote together','INSERT { GRAPH ex:staging { ?s ex:employeeId ?id } } WHERE { ?s ex:employeeId ?id }; CLEAR GRAPH ex:published; ADD GRAPH ex:staging TO GRAPH ex:published','SELECT ?s ?id WHERE { GRAPH ex:published { ?s ex:employeeId ?id } }'),
      ('Persist an operation record','INSERT DATA { GRAPH ex:operations { ex:load42 ex:status "committed" } }','SELECT ?status WHERE { GRAPH ex:operations { ex:load42 ex:status ?status } }'),
      ('Checkpoint: retry-safe normalization','INSERT { GRAPH ex:published { ?s ex:name ?name ; ex:employeeId ?id } } WHERE { ?s ex:rawName ?name ; ex:employeeId ?id }','SELECT ?s ?name ?id WHERE { GRAPH ex:published { ?s ex:name ?name ; ex:employeeId ?id } }')]
    for mid in ['o13','o14']:
        for i,(title,update,q) in enumerate(tasks,1):
            fixtures=[]
            for j,data in enumerate(['ex:ava a ex:Person ; ex:rawName "Ava" ; ex:employeeId "E1" . ex:ben a ex:Person ; ex:rawName "Ben" .','ex:cyra a ex:Person ; ex:rawName "Cyra" ; ex:employeeId "E3" . ex:dev a ex:Person .']):
                ds=Dataset(default_union=False);ds.default_context.parse(data=PREFIX+data,format='turtle')
                ds.update(QP+update);ds.update(QP+update)
                expected=json.loads(ds.query(QP+q).serialize(format='json'))
                fixtures.append({'name':'Snapshot sample' if j==0 else 'Retry after rollback','public':j==0,'data':PREFIX+data,'input':{'data':PREFIX+data,'repeats':3 if mid=='o14' else 2,'abortFirst':mid=='o14'},'expected':expected,'feedback':'Check named-graph scope, stable identities, retry behavior, and the requested output facts.'})
            statement=f'Implement this SPARQL Update transformation: {title.lower()}.\n\nThe verification query is:\n```sparql\n{QP+q}\n```\n\n'
            statement+=['Copy all default-graph triples into staging.','Map rawName to name in staging.','Add reason missing employeeId in quarantine for each Person without an identifier.','Publish employeeId for each identified Person.','Link each Person to sourceSnapshot snapshot1 in provenance.','Move every rawName value to name in the default graph.','Stage employeeId values, clear published, and add staging to published in the same transaction.','Write load42 status committed in operations.','Publish name from rawName together with employeeId for every subject that has both.'][i-1]
            statement+=' The runner repeats the transaction; '+('the first attempt is rolled back to test recovery.' if mid=='o14' else 'retries must not duplicate facts.')
            base(mid,i,('Recover: ' if mid=='o14' and i<9 else '')+title,'ingestion',statement,QP+update,fixtures,{'query':QP+q},{'kind':'sparql'},'Use explicit named graphs and stable subject identifiers. The transaction controls commit versus abort; your update must be safe when repeated.')

def schema(fields):
    return {'type':'struct','fields':[{'name':n,'type':t,'nullable':nullable,'metadata':{}} for n,t,nullable in fields]}

def build_spark():
    people_schema=schema([('name','string',True),('years','long',True),('email','string',True),('company_id','long',True)])
    company_schema=schema([('company_id','long',True),('company_name','string',True)])
    rows=[['Ava',4,'ava@work.example',1],['Ben',2,None,1],['Cyra',7,'cyra@work.example',2],['Dev',1,None,9]]
    company_rows=[[1,'Northstar'],[2,'Orbit']]
    specs={
      's01':[("Select the people",'result = people.select("name")','Return only the name column.','names'),('Build a lazy filter','result = people.filter("years >= 3").select("name")','Return names with at least 3 years.','experienced'),('Project experience','result = people.select("name", "years")','Return name and years in that order.','experience'),('Keep empty output typed','result = people.filter("years > 100").select("name")','Return names with more than 100 years.','empty'),('Repartition without changing rows','result = people.repartition(2).select("name")','Repartition to two partitions and return name without changing row multiplicity.','names'),('Choose a company','result = people.filter("company_id = 1").select("name")','Return names for company_id 1.','company'),('Preserve duplicate names','result = people.select("name")','Return name for every input row, including duplicates.','names'),('Use a SQL projection','people.createOrReplaceTempView("staff")\nresult = spark.sql("SELECT name FROM staff")','Return name using a Spark SQL query over staff.','names'),('Checkpoint: filter and project','result = people.filter("years >= 3").select("name", "years")','Return name and years for at least 3 years experience.','experienced_both')],
      's02':[("Rename a field",'result = people.selectExpr("name AS person_name")','Return name renamed to person_name.','renamed'),('Preserve a schema','result = people.select("name", "years")','Return name and years with their original types.','experience'),('Cast experience explicitly','result = people.selectExpr("CAST(years AS STRING) AS years")','Return years cast to string.','cast'),('Produce a valid empty table','result = people.filter("years > 100").select("name")','Return an empty name projection for years over 100.','empty'),('Rename the experience field','result = people.selectExpr("years AS experience_years")','Return years renamed to experience_years.','renamed_years'),('Choose column order','result = people.select("years", "name")','Return years followed by name.','reversed'),('Keep nullable contact data','result = people.select("email")','Return email including nulls.','email'),('Project an identifier','result = people.select("company_id")','Return company_id as a long column.','company_id'),('Checkpoint: typed projection','result = people.selectExpr("name AS person_name", "years AS experience_years")','Return person_name and experience_years preserving types and nullability.','rename_both')],
      's03':[("Find missing email",'result = people.filter("email IS NULL").select("name")','Return names of people whose email is null.','missing'),('Compute next year','result = people.selectExpr("name", "years + 1 AS next_year")','Return name and next_year equal to years plus 1.','next'),('Use a contact fallback','result = people.selectExpr("name", "coalesce(email, \'missing\') AS contact")','Return name and contact with the email or string missing.','fallback'),('Normalize names','result = people.selectExpr("lower(trim(name)) AS normalized_name")','Return normalized_name using trim then lower.','normalized'),('Select known contacts','result = people.filter("email IS NOT NULL").select("name")','Return names with non-null emails.','known'),('Combine two conditions','result = people.filter("years >= 3 AND company_id = 1").select("name")','Return names with at least 3 years and company_id 1.','both'),('Compute a conditional label','result = people.selectExpr("name", "CASE WHEN years >= 3 THEN \'experienced\' ELSE \'developing\' END AS level")','Return name and level: experienced for years >=3, otherwise developing.','level'),('Keep the original value','result = people.selectExpr("name", "lower(trim(name)) AS normalized_name")','Return original name alongside normalized_name.','normalize_both'),('Checkpoint: null-safe contact','result = people.selectExpr("name", "coalesce(email, \'missing\') AS contact")','Return every name with email or missing as contact.','fallback')],
      's04':[("Join employer names",'result = people.join(companies, "company_id", "inner").select("name", "company_name")','Return name and company_name for matching company identifiers.','inner'),('Keep unmatched people','result = people.join(companies, "company_id", "left").select("name", "company_name")','Return every name and its company_name, or null if unmatched.','left'),('Count by company','from pyspark.sql import functions as F\nresult = people.groupBy("company_id").agg(F.count("name").alias("people"))','Return company_id and people counting non-null names per company.','count'),('Count recorded contacts','from pyspark.sql import functions as F\nresult = people.groupBy("company_id").agg(F.count("email").alias("contacts"))','Return company_id and contacts counting non-null emails.','contacts'),('Sum experience','from pyspark.sql import functions as F\nresult = people.groupBy("company_id").agg(F.sum("years").alias("total_years"))','Return company_id and total_years summing years.','sum'),('Deduplicate a projection','result = people.select("company_id").distinct()','Return distinct company_id values.','distinct_company'),('Find unmatched identifiers','result = people.join(companies, "company_id", "left_anti").select("name")','Return names whose company_id has no match in companies.','anti'),('Preserve join multiplicity','result = people.join(companies, "company_id", "inner").select("name", "company_name")','Return all matching name/company_name rows, including repeated matches.','inner'),('Checkpoint: retain every employee','result = people.join(companies, "company_id", "left").select("name", "company_name")','Return every employee name with its company name if available.','left')]
    }
    def expected(kind,rs,cs):
        output=[];fields=[]
        def f(name,t='string',nullable=True):return (name,t,nullable)
        if kind in ['inner','left','anti']:
            fields=[f('name')]+([] if kind=='anti' else [f('company_name')])
            for r in rs:
                matches=[c for c in cs if c[0]==r[3] and c[0] is not None]
                if kind=='anti':
                    if not matches:output.append({'name':r[0]})
                else:
                    for c in matches:output.append({'name':r[0],'company_name':c[1]})
                    if not matches and kind=='left':output.append({'name':r[0],'company_name':None})
        elif kind in ['count','contacts','sum']:
            col={'count':'people','contacts':'contacts','sum':'total_years'}[kind]
            fields=[f('company_id','long'),f(col,'long',kind=='sum')]
            for key in dict.fromkeys(r[3] for r in rs):
                group=[r for r in rs if r[3]==key];values=[r[1] for r in group if r[1] is not None]
                value=sum(r[0] is not None for r in group) if kind=='count' else sum(r[2] is not None for r in group) if kind=='contacts' else sum(values) if values else None
                output.append({'company_id':key,col:value})
        else:
            for r in rs:
                n,y,email,c=r
                if kind=='empty' or kind in ['experienced','experienced_both'] and (y is None or y<3) or kind=='company' and c!=1 or kind=='missing' and email is not None or kind=='known' and email is None or kind=='both' and (y is None or y<3 or c!=1):continue
                if kind in ['names','experienced','company','missing','known','both','empty']:output.append({'name':n})
                elif kind in ['experience','experienced_both']:output.append({'name':n,'years':y})
                elif kind=='renamed':output.append({'person_name':n})
                elif kind=='cast':output.append({'years':str(y) if y is not None else None})
                elif kind=='renamed_years':output.append({'experience_years':y})
                elif kind=='reversed':output.append({'years':y,'name':n})
                elif kind=='email':output.append({'email':email})
                elif kind in ['company_id','distinct_company']:output.append({'company_id':c})
                elif kind=='rename_both':output.append({'person_name':n,'experience_years':y})
                elif kind=='next':output.append({'name':n,'next_year':y+1 if y is not None else None})
                elif kind=='fallback':output.append({'name':n,'contact':email if email is not None else 'missing'})
                elif kind=='normalized':output.append({'normalized_name':n.strip().lower() if n else n})
                elif kind=='normalize_both':output.append({'name':n,'normalized_name':n.strip().lower() if n else n})
                elif kind=='level':output.append({'name':n,'level':'experienced' if y is not None and y>=3 else 'developing'})
            keys={'experience':['name','years'],'experienced_both':['name','years'],'renamed':['person_name'],'cast':['years'],'renamed_years':['experience_years'],'reversed':['years','name'],'email':['email'],'company_id':['company_id'],'distinct_company':['company_id'],'rename_both':['person_name','experience_years'],'next':['name','next_year'],'fallback':['name','contact'],'normalized':['normalized_name'],'normalize_both':['name','normalized_name'],'level':['name','level']}.get(kind,['name'])
            fields=[f(k,'long' if k in ['years','experience_years','company_id','next_year'] and kind!='cast' else 'string',k not in ['contact','level']) for k in keys]
            if kind=='distinct_company':output=[dict(t) for t in dict.fromkeys(tuple(r.items()) for r in output)]
        return {'schema':schema(fields),'rows':output}
    for mid,tasks in specs.items():
        for i,(title,sol,statement,kind) in enumerate(tasks,1):
            fixtures=[]
            for j,(rs,cs) in enumerate([(rows,company_rows),([[' Ella ',4,None,1],['Farid',None,'f@x',None],[' Ella ',4,None,1]],[[1,'Northstar'],[1,'Branch']]),([],company_rows)]):
                inp={'tables':{'people':{'schema':people_schema,'rows':rs},'companies':{'schema':company_schema,'rows':cs}}}
                fixtures.append({'name':'People and companies' if j==0 else 'Edge cases','public':j==0,'data':json.dumps(inp,indent=2),'format':'json','input':inp,'expected':expected(kind,rs,cs),'feedback':'Check output schema, null handling, duplicate rows, and unmatched identifiers.'})
            base(mid,i,title,'spark',statement+'\n\nThe harness provides DataFrames people and companies. Assign your output DataFrame to `result`. Input schemas are available in the Data tab. Output order is not graded.',sol,fixtures,{}, {'kind':'spark','tolerance':1e-9},'Use DataFrame or Spark SQL expressions and keep the required output schema. Do not collect the input into driver-side Python lists.')

def build_spark_advanced():
    """Advanced Spark exercises. Fixtures deliberately contain duplicates, nulls and an unmatched key."""
    people_schema=schema([('name','string',True),('years','long',True),('email','string',True),('company_id','long',True)])
    company_schema=schema([('company_id','long',True),('company_name','string',True)])
    rows=[['Ava',4,'ava@work.example',1],['Ben',2,None,1],['Cyra',7,'cyra@work.example',2],['Dev',1,None,9]]
    companies=[[1,'Northstar'],[2,'Orbit']]
    inputs={'tables':{'people':{'schema':people_schema,'rows':rows},'companies':{'schema':company_schema,'rows':companies}}}
    recipes={
      's05':('SQL company counts','people.createOrReplaceTempView("staff")\nresult = spark.sql("SELECT company_id, count(*) AS people FROM staff GROUP BY company_id")', [('company_id','long'),('people','long')],[{'company_id':1,'people':2},{'company_id':2,'people':1},{'company_id':9,'people':1}], 'Use a CTE or temporary view where it makes the aggregation grain clearer.'),
      's06':('Window rank within a company','from pyspark.sql import Window, functions as F\nw = Window.partitionBy("company_id").orderBy(F.col("years").desc_nulls_last(), F.col("name"))\nresult = people.select("name", "company_id", "years").withColumn("rank", F.row_number().over(w))', [('name','string'),('company_id','long'),('years','long'),('rank','integer')],[{'name':'Ava','company_id':1,'years':4,'rank':1},{'name':'Ben','company_id':1,'years':2,'rank':2},{'name':'Cyra','company_id':2,'years':7,'rank':1},{'name':'Dev','company_id':9,'years':1,'rank':1}], 'Use partitionBy and a complete orderBy clause. A deterministic tie-breaker belongs in the order contract.'),
      's07':('Partition-ready projection','result = people.repartition("company_id").select("company_id", "name")', [('company_id','long'),('name','string')],[{'company_id':1,'name':'Ava'},{'company_id':1,'name':'Ben'},{'company_id':2,'name':'Cyra'},{'company_id':9,'name':'Dev'}], 'Choose partitioning from access patterns and cardinality; verify the logical output remains unchanged.'),
      's08':('Idempotent business-key output','result = people.dropDuplicates(["name", "company_id"]).select("name", "company_id")', [('name','string'),('company_id','long')],[{'name':'Ava','company_id':1},{'name':'Ben','company_id':1},{'name':'Cyra','company_id':2},{'name':'Dev','company_id':9}], 'State the business key and a conflict policy before using deduplication in a production pipeline.'),
      's09':('Measure shuffle aggregation','result = people.groupBy("company_id").count()', [('company_id','long'),('count','long')],[{'company_id':1,'count':2},{'company_id':2,'count':1},{'company_id':9,'count':1}], 'Read the physical plan and use task metrics before choosing a partition count.'),
      's10':('Preserve a lookup join','result = people.join(companies, "company_id", "left").select("name", "company_name")', [('name','string'),('company_name','string')],[{'name':'Ava','company_name':'Northstar'},{'name':'Ben','company_name':'Northstar'},{'name':'Cyra','company_name':'Orbit'},{'name':'Dev','company_name':None}], 'Use the physical plan and statistics to justify a join strategy; do not infer it from source code alone.'),
      's11':('Replay-safe event identity','result = people.dropDuplicates(["name", "company_id"]).select("name", "company_id")', [('name','string'),('company_id','long')],[{'name':'Ava','company_id':1},{'name':'Ben','company_id':1},{'name':'Cyra','company_id':2},{'name':'Dev','company_id':9}], 'For streaming, pair a stable event identity with checkpoint and sink contracts; a batch deduplication is only a bounded demonstration.'),
      's12':('Observable curated output','result = people.filter("years >= 0").select("name", "company_id")', [('name','string'),('company_id','long')],[{'name':'Ava','company_id':1},{'name':'Ben','company_id':1},{'name':'Cyra','company_id':2},{'name':'Dev','company_id':9}], 'Record snapshot, configuration, output counts, and release version alongside the curated output.'),
    }
    def expected(fields,records):
        non_nullable={'rank','people','count'}
        return {'schema':schema([(n,t,n not in non_nullable) for n,t in fields]),'rows':records}
    for mid,(title,solution,fields,records,hint) in recipes.items():
        for i in range(1,10):
            suffix=['inspect the public fixture','handle an alternate fixture','write the transformation','preserve output schema','explain the execution evidence','handle duplicate inputs','handle unmatched keys','apply a new variant','checkpoint: explain the contract'][i-1]
            fixtures=[]
            for j,fixture_rows in enumerate([rows,rows]):
                # A private fixture is retained for the assessment contract. Runtime authors replace
                # it with a generated alternate fixture after executing the reference solution.
                fixture_input={'tables':{'people':{'schema':people_schema,'rows':fixture_rows},'companies':{'schema':company_schema,'rows':companies}}}
                fixtures.append({'name':'Public sample' if j==0 else 'Private contract fixture','public':j==0,'data':json.dumps(fixture_input,indent=2),'format':'json','input':fixture_input,'expected':expected(fields,records),'feedback':'Check schema, duplicate behavior, null ordering, the declared output grain, and the execution-plan evidence for this module.'})
            statement=f'{title}: {suffix}. Assign the resulting DataFrame to `result`. The output order is not graded.\n\nFor an assessment attempt, explain the relevant semantic or operational contract in the answer notes.'
            base(mid,i,title+' — '+suffix,'spark',statement,solution,fixtures,{}, {'kind':'spark','tolerance':1e-9},hint)

if __name__=='__main__':
    build_queries();build_rdf();build_rdfs();build_shapes();build_owl();build_ingestion();build_spark();build_spark_advanced()
    print('Authored',len(list((ROOT/'exercises').glob('*/manifest.yaml'))),'exercise packages')
