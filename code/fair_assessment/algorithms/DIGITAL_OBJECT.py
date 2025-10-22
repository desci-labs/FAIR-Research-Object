import logging
import traceback
from rocrate.rocrate import ROCrate
import os, sys
import json

sys.path.insert(0, os.path.dirname(__file__))
from FAIROS_DATASET_FUJI import FAIROS_DATASET_FUJI

logger = logging.getLogger(__name__)

class DIGITAL_OBJECT:
    def execute_algorithm_uri(uri, ticket):
        dataset = FAIROS_DATASET_FUJI()
        tests_results = dataset.execute_algorithm_uri(uri, ticket)

        # Write the JSON-LD to a file
        output_file_results = f"C:\\Users\\egonzalez\\tests_results\\assessment-results-{ticket}.jsonld"
        with open(output_file_results, "w", encoding="utf-8") as f:
            json.dump(tests_results, f, ensure_ascii=False, indent=2)
    
    def get_id():
        return "DIGITAL_OBJECT"
    def getTTL():
        return "simple"