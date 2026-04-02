import sys
import os

try:
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"CWD: {os.getcwd()}")
    sys.path.insert(0, os.getcwd())
    
    import app.db.session
    print("app.db.session imported")
    
    import app.db.models
    print("app.db.models imported")
    
    from app.reconciliation.ontology import OntologyResolver
    print("OntologyResolver imported")
    
    resolver = OntologyResolver()
    print("OntologyResolver initialized")
    print(f"Concepts: {resolver.get_concept_names()}")
    
    from app.reconciliation.engine import ReconciliationEngine
    print("ReconciliationEngine imported")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
