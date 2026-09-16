package lab.graph;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.*;
import org.apache.jena.shacl.*;
import org.apache.jena.update.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.StringDocumentSource;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.profiles.OWL2DLProfile;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.HermiT.ReasonerFactory;

public class Runner {
  static final ObjectMapper JSON = new ObjectMapper();
  public static void main(String[] args) throws Exception {
    ObjectNode result;
    try { result = run(JSON.readTree(Files.readString(Path.of("/input.json")))); }
    catch (Throwable e) {
      e.printStackTrace(System.err);
      result = JSON.createObjectNode().put("error",e.getClass().getSimpleName()+": "+String.valueOf(e.getMessage()).substring(0,Math.min(2500,String.valueOf(e.getMessage()).length())));
    }
    Files.writeString(Path.of("/output/result.json"),JSON.writeValueAsString(result));
  }
  static Model model(String data) {
    Model m=ModelFactory.createDefaultModel();
    RDFParser.fromString(data).lang(Lang.TURTLE).parse(m);
    return m;
  }
  static ObjectNode run(JsonNode input) throws Exception {
    String runner=input.path("runner").asText();
    JsonNode files=input.path("files"), fixture=input.path("fixture"), contract=input.path("contract");
    if (runner.equals("owl")) return owl(files.path("ontology.ttl").asText(),fixture);
    Model data=model(fixture.path("data").asText(""));
    if (runner.equals("shacl")) {
      Model shapes=model(files.path("shapes.ttl").asText());
      ValidationReport report=ShaclValidator.get().validate(Shapes.parse(shapes.getGraph()),data.getGraph());
      ObjectNode result=JSON.createObjectNode().put("conforms",report.conforms());
      ArrayNode components=result.putArray("components"), violations=result.putArray("violations");
      report.getEntries().forEach(e->{
        if(e.sourceConstraintComponent()!=null) components.add(e.sourceConstraintComponent().toString());
        ObjectNode v=violations.addObject();
        v.put("focus",String.valueOf(e.focusNode())); v.put("path",String.valueOf(e.resultPath())); v.put("message",String.valueOf(e.message()));
      });
      return result;
    }
    if (runner.equals("rdf")) {
      data.add(model(files.path("ontology.ttl").asText()));
      if(contract.path("inference").asText().equals("rdfs")) data=ModelFactory.createRDFSModel(data);
      return query(DatasetFactory.create(data),contract.path("query").asText());
    }
    if (runner.equals("ingestion")) {
      Dataset ds=TDB2Factory.connectDataset("/work/tdb");
      ds.begin(ReadWrite.WRITE);
      try { ds.getDefaultModel().add(data);ds.commit(); } finally {ds.end();}
      String update=files.path("update.rq").asText();
      int repeats=fixture.path("repeats").asInt(1);
      for(int i=0;i<repeats;i++) {
        ds.begin(ReadWrite.WRITE);
        try {
          UpdateAction.parseExecute(update,ds);
          if(fixture.path("abortFirst").asBoolean(false)&&i==0) ds.abort();else ds.commit();
        } finally { ds.end(); }
      }
      ds.begin(ReadWrite.READ);
      try {return query(ds,contract.path("query").asText());} finally {ds.end();ds.close();}
    }
    Dataset ds=DatasetFactory.createTxnMem();
    ds.setDefaultModel(data);
    Iterator<Map.Entry<String,JsonNode>> graphs=fixture.path("graphs").fields();
    while(graphs.hasNext()){var g=graphs.next();ds.addNamedModel(g.getKey(),model(g.getValue().asText()));}
    return query(ds,files.path("query.rq").asText());
  }
  static ObjectNode query(Dataset ds,String text) throws Exception {
    Query q=QueryFactory.create(text);
    // External SERVICE and loading are additionally prevented by the network namespace.
    try(QueryExecution execution=QueryExecutionFactory.create(q,ds)) {
      if(q.isAskType()) return JSON.createObjectNode().put("boolean",execution.execAsk());
      if(q.isConstructType()) {
        StringWriter out=new StringWriter(); RDFDataMgr.write(out,execution.execConstruct(),Lang.TURTLE);
        return JSON.createObjectNode().put("graph",out.toString());
      }
      if(!q.isSelectType()) throw new IllegalArgumentException("Use SELECT, ASK, or CONSTRUCT for this exercise");
      ByteArrayOutputStream out=new ByteArrayOutputStream();
      ResultSetFormatter.outputAsJSON(out,execution.execSelect());
      if(out.size()>1_500_000) throw new IllegalArgumentException("Result exceeds the row output allowance");
      return (ObjectNode)JSON.readTree(out.toByteArray());
    }
  }
  static ObjectNode owl(String source,JsonNode fixture) throws Exception {
    // Imports must be bundled; no remote resolution, even in developer mode.
    if(source.contains("owl:imports")||source.contains("http://www.w3.org/2002/07/owl#imports")) throw new IllegalArgumentException("Use a bundled ontology without remote imports");
    var manager=OWLManager.createOWLOntologyManager();
    OWLOntology ontology=manager.loadOntologyFromOntologyDocument(new StringDocumentSource(source+"\n"+fixture.path("data").asText("")));
    if(!new OWL2DLProfile().checkOntology(ontology).isInProfile()) throw new IllegalArgumentException("The ontology is outside OWL 2 DL; check declarations and property restrictions");
    OWLReasoner reasoner=new ReasonerFactory().createReasoner(ontology,new SimpleConfiguration(45000));
    try {
      ObjectNode result=JSON.createObjectNode().put("consistent",reasoner.isConsistent());
      if(!result.path("consistent").asBoolean()) return result;
      if(fixture.has("checkAxioms")) {
        var checkManager=OWLManager.createOWLOntologyManager();
        var required=checkManager.loadOntologyFromOntologyDocument(new StringDocumentSource(fixture.path("checkAxioms").asText()));
        result.put("requiredAxioms",required.getLogicalAxioms().stream().allMatch(reasoner::isEntailed));
      }
      OWLDataFactory f=manager.getOWLDataFactory();
      for(JsonNode c:fixture.path("checks")) {
        String kind=c.path("kind").asText(), key=c.path("id").asText();
        OWLClass cls=f.getOWLClass(IRI.create(c.path("class").asText()));
        boolean answer;
        if(kind.equals("satisfiable")) answer=reasoner.isSatisfiable(cls);
        else if(kind.equals("subclass")) answer=reasoner.isEntailed(f.getOWLSubClassOfAxiom(cls,f.getOWLClass(IRI.create(c.path("super").asText()))));
        else answer=reasoner.isEntailed(f.getOWLClassAssertionAxiom(cls,f.getOWLNamedIndividual(IRI.create(c.path("individual").asText()))));
        result.put(key,answer);
      }
      return result;
    } finally {reasoner.dispose();}
  }
}
