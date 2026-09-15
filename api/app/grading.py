"""Trusted output comparators. Never execute learner Python in this process."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import json
import math
from rdflib import Graph, BNode, URIRef, Literal, Namespace
from rdflib.compare import isomorphic

NS = Namespace('urn:graphlab:result:')

def term(value):
    if value is None:
        return None
    kind = value.get('type')
    if kind == 'uri':
        return URIRef(value['value'])
    if kind == 'bnode':
        return BNode(value['value'])
    return Literal(value['value'], lang=value.get('xml:lang'), datatype=value.get('datatype'), normalize=False)

def result_graph(result, ordered=False):
    """Encode each row as a distinct blank node, preserving bags and bnode identity."""
    graph = Graph()
    variables = result.get('head', {}).get('vars', [])
    graph.add((NS.root, NS.variables, Literal(json.dumps(sorted(variables)))))
    # Separate result blank nodes from row blank nodes.
    labels = {}
    for index, row in enumerate(result.get('results', {}).get('bindings', [])):
        node = BNode()
        graph.add((NS.root, NS.row, node))
        if ordered:
            graph.add((node, NS.position, Literal(index)))
        for variable in variables:
            raw = row.get(variable)
            if raw is None:
                continue
            value = term(raw)
            if isinstance(value, BNode):
                value = labels.setdefault(str(value), BNode())
            graph.add((node, URIRef(str(NS) + 'binding/' + variable), value))
    return graph

def compare_sparql(actual, expected, ordered=False):
    if 'boolean' in expected:
        return type(actual.get('boolean')) is bool and actual['boolean'] == expected['boolean']
    if set(actual.get('head',{}).get('vars',[])) != set(expected.get('head',{}).get('vars',[])):
        return False
    return isomorphic(result_graph(actual, ordered), result_graph(expected, ordered))

def compare_graph(actual, expected):
    return isomorphic(Graph().parse(data=actual, format='turtle'), Graph().parse(data=expected, format='turtle'))

def equivalent_value(a, b, tolerance=0):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int,float)) and isinstance(b, (int,float)):
        return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equivalent_value(x,y,tolerance) for x,y in zip(a,b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent_value(a[k], b[k], tolerance) for k in a)
    return type(a) is type(b) and a == b

def compare_spark(actual, expected, ordered=False, tolerance=0):
    if actual.get('schema') != expected.get('schema'):
        return False
    rows, reference = actual.get('rows',[]), expected.get('rows',[])
    if len(rows) != len(reference):
        return False
    if ordered:
        return all(equivalent_value(a,b,tolerance) for a,b in zip(rows,reference))
    # Bipartite matching avoids greedy tolerance comparisons producing false negatives.
    matches = {}
    def assign(i, seen):
        for j, row in enumerate(reference):
            if j not in seen and equivalent_value(rows[i], row, tolerance):
                seen.add(j)
                if j not in matches or assign(matches[j], seen):
                    matches[j] = i
                    return True
        return False
    return all(assign(i, set()) for i in range(len(rows)))

def compare(actual, expected, contract):
    kind = contract['kind']
    if kind == 'sparql':
        return compare_sparql(actual, expected, contract.get('ordered',False))
    if kind == 'graph':
        return compare_graph(actual['graph'], expected['graph'])
    if kind == 'spark':
        return compare_spark(actual,expected,contract.get('ordered',False),contract.get('tolerance',0))
    if kind == 'shacl':
        return actual.get('conforms') == expected['conforms'] and (not expected.get('components') or set(expected['components']).issubset(set(actual.get('components',[]))))
    if kind == 'owl':
        if actual.get('consistent') is not True:
            return expected.get('consistent') is False
        return all(actual.get(k) == v for k,v in expected.items())
    return actual == expected
