from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE, N3, RDF, RDFXML, CSV, TSV, JSONLD, QueryResult
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException
from typing import Any

from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import DefinedNamespace, RDF, VOID

class SD(DefinedNamespace):
    _NS = Namespace('http://www.w3.org/ns/sparql-service-description#')
    _fail = True

    endpoint: URIRef
    feature: URIRef
    name: URIRef
    graph: URIRef
    defaultGraph: URIRef
    defaultDataset: URIRef
    namedGraph: URIRef
    supportedLanguage: URIRef
    supportedVersion: URIRef
    resultFormat: URIRef

    Service: URIRef
    Dataset: URIRef
    Graph: URIRef

    SPARQLQuery: URIRef
    SPARQLUpdate: URIRef

    SPARQL10Query: URIRef
    SPARQL11Query: URIRef
    SPARQL11Update: URIRef

    BasicFederatedQuery: URIRef

SPARQL = Namespace('http://www.w3.org/ns/sparql#')
FORMATS = Namespace('http://www.w3.org/ns/formats/')

class QueryResultBinding:
    def __init__(self, result):
        self.data = result

    

class QueryResult:
    def __init__(self, result):
        self.data = result

    @property
    def bindings(self) -> list[dict[str]]:
        return self.data['results']['bindings']
    

    def get(self, binding: str, default=None) -> str | None:
        try:
            return self.bindings[0][binding]['value']
        except (KeyError, IndexError):
            return default


def query(sparql: SPARQLWrapper, query: str, format: str = JSON) -> QueryResult | None:
    old_format = sparql.returnFormat
    sparql.setReturnFormat(format)

    sparql.setQuery(query)
    result = None
    try:
        ret = sparql.query()
        if 200 <= ret.response.status < 300:
            result = QueryResult(ret.convert())
    except SPARQLWrapperException:
        pass

    sparql.setReturnFormat(old_format)

    return result


def _default_graph_triples(sparql: SPARQLWrapper) -> int | None:
    res = query(sparql, """
        SELECT (COUNT(*) AS ?triples)
        WHERE {
            ?s ?p ?o
        }
    """)
    return int(res.get('triples') or 0)

def _default_graph_classes(sparql: SPARQLWrapper) -> int | None:
    res = query(sparql, """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT (COUNT(*) AS ?classes)
        WHERE { 
            ?s a rdf:type
        }
    """)
    return int(res.get('classes') or 0)

def _default_graph_predicates(sparql: SPARQLWrapper) -> int | None:
    res = query(sparql, """
        SELECT DISTINCT (COUNT(*) AS ?predicates)
        WHERE {
            ?s ?p ?o
        }
    """)
    return int(res.get('predicates') or 0)

def _get_named_graphs(sparql: SPARQLWrapper) -> list[str] | None:
    res = query(sparql, """
        SELECT ?graph
        WHERE {
            GRAPH ?graph {
                ?s ?p ?o
            }
        }        
    """)
    return [binding['value'] for binding in res.bindings]

def _supports_query(sparql: SPARQLWrapper) -> bool:
    return query(sparql, "SELECT ?x WHERE {}") is not None

def _supports_query_11(sparql: SPARQLWrapper) -> bool:
    # Aggregates (e.g. COUNT) are a feature added in SPARQL 1.1
    return query(sparql, """
        PREFIX ex: <http://example.com/#>
        SELECT COUNT(*)
        WHERE {
            ex:s ex:p ex:o
        }
    """) is not None

def _supports_query_12(sparql: SPARQLWrapper) -> bool:
    # Triple functions (e.g. OBJECT) were introduced in SPARQL 1.2
    return query(sparql, """
        SELECT ?s
        WHERE {
            BIND(OBJECT("") AS ?s)
        }    
    """) is not None

def _supports_update(sparql: SPARQLWrapper) -> bool:
    # Triple functions were introduced in SPARQL 1.2
    sparql.setQuery("INSERT DATA { <http://example.com/#s> <http://example.com/#p> <http://example.com/#o> . }")
    sparql.setMethod('POST')
    try:
        ret = sparql.query()
        result = 200 <= ret.response.status < 300
    except SPARQLWrapperException:
        result = False

    if result:
        # Cleanup
        sparql.setQuery("DELETE DATA { <http://example.com/#s> <http://example.com/#p> <http://example.com/#o> . }")
        sparql.query()
    
    sparql.setMethod('GET')
    return result

def _supports_federated_queries(sparql: SPARQLWrapper) -> bool:
    return query(sparql, """
        SELECT ?s
        WHERE {
            SERVICE <https://query.wikidata.org/bigdata/namespace/wdq/sparql> {
                ?s ?p ?o LIMIT 1
            }
        }
    """) is not None

def _supports_format(sparql: SPARQLWrapper, format: str, query: str) -> bool:
    sparql.setQuery(query)
    sparql.setReturnFormat(format)
    try:
        ret = sparql.query()
        return ret._get_responseFormat() == format
    except SPARQLWrapperException:
        return False

def _supported_formats(sparql: SPARQLWrapper) -> list[str]:
    SELECT_QUERY = 'SELECT ?s WHERE { ?s <http://example.com/#p> "" }'
    CONSTRUCT_QUERY = 'CONSTRUCT { ?s <http://example.com/#p> "" } WHERE { ?s <http://example.com/#p> "" }'

    SELECT_FORMATS = [JSON, XML, CSV, TSV]
    CONSTRUCT_FORMATS = [TURTLE, N3, RDFXML, JSONLD]

    W3_FORMATS = {
        JSON: 'SPARQL_Results_JSON',
        XML: 'SPARQL_Results_XML',
        CSV: 'SPARQL_Results_CSV',
        TSV: 'SPARQL_Results_TSV',
        TURTLE: 'Turtle',
        N3: 'N3',
        RDFXML: 'RDF_XML',
        JSONLD: 'JSON-LD',
    }

    return \
        [W3_FORMATS[fmt] for fmt in SELECT_FORMATS if _supports_format(sparql, fmt, SELECT_QUERY)] +\
        [W3_FORMATS[fmt] for fmt in CONSTRUCT_FORMATS if _supports_format(sparql, fmt, CONSTRUCT_QUERY)]
    

def generate_service_description(endpoint: str, includeVoID=False) -> Graph:
    sparql = SPARQLWrapper(endpoint)
    sparql.setReturnFormat(JSON)

    graph = Graph()
    graph.bind('rdf', RDF)
    graph.bind('sd', SD)
    graph.bind('sparql', SPARQL)
    graph.bind('format', FORMATS)

    this_service = BNode()
    default_dataset = BNode()
    default_graph = BNode()

    graph.add((this_service, RDF.type, SD.Service))
    graph.add((this_service, SD.endpoint, URIRef(endpoint)))

    graph.add((default_dataset, RDF.type, SD.Dataset))
    graph.add((this_service, SD.defaultDataset, default_dataset))

    graph.add((default_graph, RDF.type, SD.Graph))
    graph.add((default_dataset, SD.defaultGraph, default_graph))

    if _supports_query(sparql):
        graph.add((this_service, SD.supportedLanguage, SD.SPARQLQuery))
        graph.add((this_service, SD.supportedLanguage, SD.SPARQL10Query))
        graph.add((this_service, SD.supportedVersion, SPARQL['version-1.0']))

        if _supports_query_11(sparql):
            graph.add((this_service, SD.supportedLanguage, SD.SPARQL11Query))
            graph.add((this_service, SD.supportedVersion, SPARQL['version-1.1']))

        if _supports_query_12(sparql):
            graph.add((this_service, SD.supportedLanguage, SD.SPARQL11Query))
            graph.add((this_service, SD.supportedVersion, SPARQL['version-1.2-basic']))
    
    if _supports_update(sparql):
        graph.add((this_service, SD.supportedLanguage, SD.SPARQLUpdate))
        graph.add((this_service, SD.supportedLanguage, SD.SPARQL11Update))

    if _supports_federated_queries(sparql):
        graph.add((this_service, SD.feature, SD.BasicFederatedQuery))

    if (named_graphs := _get_named_graphs(sparql)):
        for named_graph in named_graphs:
            ng = BNode()
            graph.add((default_dataset, SD.namedGraph, ng))
            graph.add((ng, SD.name, Literal(named_graph)))

    for fmt in _supported_formats(sparql):
        graph.add((this_service, SD.resultFormat, FORMATS[fmt]))
    sparql.setReturnFormat(JSON)

    # SD.feature DereferencesURIs
    # SD.feature UnionDefaultGraph would require checking the entire graph against its named conterparts
    # SD.feature RequiresDataset 
    # SD.feature EmptyGraphs would require an ampty graph on the backend 
    # Entailment Regimes: Not detectable from the outside because non-existent triples are inferred before/while executing the query
    # ExtensionFunctions: Not detectable because non-documented. Would need to check all possible functions (= all possible function names) 
    # ExtensionAggregates: Not detectable because non-documented. Would need to check all possible aggregates (= all possible aggregate names) 
    # availableGraphs : The same as the default dataset?
    # inputFormat

    if includeVoID:
        graph.bind('void', VOID)

        if (count := _default_graph_triples(sparql)):
            graph.add((default_graph, VOID.triples, Literal(count)))
        
        if (count := _default_graph_classes(sparql)):
            graph.add((default_graph, VOID.classes, Literal(count)))

        if (count := _default_graph_predicates(sparql)):
            graph.add((default_graph, VOID.properties, Literal(count)))


    return graph

sd_graph = generate_service_description(
    'https://opendata.leipzig.de/sparql',
    includeVoID=True)

v = sd_graph.serialize(format='turtle')
print(v)
