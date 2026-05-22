# SPARQL SD Deduction

Generating service descriptions from the outside.

## Usage

```bash
python main.py <endpoint> [--output <file>] [--void]
```

Produces a Turtle file containing a valid service description for the endpoint.

Example output for the OpenData endpoint Leipzig:

```turtle
@prefix format: <http://www.w3.org/ns/formats/> .
@prefix sd: <http://www.w3.org/ns/sparql-service-description#> .
@prefix sparql: <http://www.w3.org/ns/sparql#> .
@prefix void: <http://rdfs.org/ns/void#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] a sd:Service ;
    sd:defaultDataset [ a sd:Dataset ;
            sd:defaultGraph [ a sd:Graph ;
                    void:properties 7338 ;
                    void:triples 7338 ] ] ;
    sd:endpoint <https://opendata.leipzig.de/sparql> ;
    sd:resultFormat format:JSON-LD,
        format:SPARQL_Results_CSV,
        format:SPARQL_Results_JSON,
        format:SPARQL_Results_TSV,
        format:SPARQL_Results_XML,
        format:Turtle ;
    sd:supportedLanguage sd:SPARQL10Query,
        sd:SPARQL11Query,
        sd:SPARQLQuery ;
    sd:supportedVersion sparql:version-1.0,
        sparql:version-1.1,
        sparql:version-1.2-basic .
```

## Missing SD options

- **DereferencesURIs**
- **UnionDefaultGraph** would require checking the entire graph against its named conterparts
- **RequiresDataset** 
- **EmptyGraphs** would require an empty graph on the backend 
- **EntailmentRegimes** not detectable from the outside because non-existent triples are inferred before/while executing the query
- **ExtensionFunctions** not detectable because non-documented. Would need to check all possible functions (= all possible function names) 
  - Could at least check common extra functions?
- **ExtensionAggregates** not detectable because non-documented. Would need to check all possible aggregates (= all possible aggregate names)
  - Could at least check common extra aggregates?
- **availableGraphs** The same as the default dataset?
- **inputFormat**
