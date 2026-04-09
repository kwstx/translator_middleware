from owlready2 import *
import os
from pathlib import Path
from app.core.config import settings

# Create a temporary ontology file if it doesn't exist
BASE_OWL_PATH = Path(__file__).parent / "base.owl"

def ensure_base_ontology():
    if not BASE_OWL_PATH.exists():
        onto = get_ontology("http://engram.ai/ontology/base.owl")
        with onto:
            class Concept(Thing): pass
            class Entity(Concept): pass
            class Field(Concept): pass
            class Operation(Concept): pass
            
            # Entities
            class Customer(Entity): pass
            class Order(Entity): pass
            class Product(Entity): pass
            
            # Fields
            class email(Field): pass
            class customer_id(Field): pass
            class first_name(Field): pass
            class last_name(Field): pass
            class phone(Field): pass
            
            # Operations
            class Create(Operation): pass
            class Update(Operation): pass
            class Delete(Operation): pass
            class Get(Operation): pass

        onto.save(file=str(BASE_OWL_PATH), format="rdfxml")

class OntologyResolver:
    def __init__(self):
        ensure_base_ontology()
        self.onto = get_ontology(str(BASE_OWL_PATH)).load()
        if not settings.LOW_MEMORY_MODE:
            self.sync_reasoner()

    def sync_reasoner(self):
        with self.onto:
            sync_reasoner()

    def get_concepts(self):
        return list(self.onto.classes())

    def get_concept_names(self):
        return [c.name for c in self.get_concepts()]

    def search_concept(self, name):
        return self.onto.search_one(label=name) or self.onto.search_one(iri=f"*{name}")

    def get_subclasses(self, cls_name):
        cls = self.search_concept(cls_name)
        if cls:
            return list(cls.subclasses())
        return []
