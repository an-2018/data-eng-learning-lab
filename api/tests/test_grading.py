from app.grading import compare_sparql,compare_graph,compare_spark

def result(rows,variables=['x']):return {'head':{'vars':variables},'results':{'bindings':rows}}
def literal(v,dt=None):return {'type':'literal','value':v,**({'datatype':dt} if dt else {})}

def test_bag_not_set():
    row={'x':literal('A')}
    assert not compare_sparql(result([row,row]),result([row]))

def test_order_only_when_requested():
    a,b={'x':literal('A')},{'x':literal('B')}
    assert compare_sparql(result([a,b]),result([b,a]))
    assert not compare_sparql(result([a,b]),result([b,a]),True)

def test_blank_node_renaming_preserves_identity():
    a={'x':{'type':'bnode','value':'a'}}
    b={'x':{'type':'bnode','value':'b'}}
    c={'x':{'type':'bnode','value':'c'}}
    assert compare_sparql(result([a,a]),result([b,b]))
    assert not compare_sparql(result([a,a]),result([b,c]))

def test_unbound_differs_from_empty_literal():
    assert not compare_sparql(result([{}]),result([{'x':literal('')}]))

def test_literal_lexical_and_language_identity():
    assert not compare_sparql(result([{'x':literal('01','http://www.w3.org/2001/XMLSchema#integer')}]),result([{'x':literal('1','http://www.w3.org/2001/XMLSchema#integer')}]))
    assert not compare_sparql(result([{'x':{'type':'literal','value':'name','xml:lang':'en'}}]),result([{'x':{'type':'literal','value':'name','xml:lang':'pt'}}]))

def test_graph_isomorphism():
    assert compare_graph('<urn:a> <urn:p> [ <urn:q> "x" ] .','<urn:a> <urn:p> _:b . _:b <urn:q> "x" .')

def test_spark_multiplicity_schema_null_and_tolerance():
    schema={'fields':[{'name':'x','type':'double','nullable':True}]}
    a={'schema':schema,'rows':[{'x':1.00000001},{'x':None}]}
    b={'schema':schema,'rows':[{'x':None},{'x':1.0}]}
    assert compare_spark(a,b,tolerance=1e-6)
    assert not compare_spark(a,{**b,'rows':[{'x':1.0},{'x':1.0}]},tolerance=1e-6)
    assert not compare_spark(a,{**b,'schema':{}},tolerance=1e-6)

def test_boolean_is_not_integer():
    assert not compare_spark({'schema':{},'rows':[{'x':True}]},{'schema':{},'rows':[{'x':1}]})
