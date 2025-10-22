import logging
from FAIROS_DATASET_FUJI import FAIROS_DATASET_FUJI
from FAIROS_DATASET_ROCRATE import FAIROS_DATASET_ROCRATE
import json

logger = logging.getLogger(__name__)

class FAIROS_DATASET:
    def execute_algorithm(self, resource, ticket):
        logger.info("Executing tests on dataset")

        fuji = FAIROS_DATASET_FUJI()
        #Execute algorithm for F-UJI
        fuji_tests_results = fuji.execute_algorithm(resource,ticket)

        #Execute algorithm for rocrate
        rocrate = FAIROS_DATASET_ROCRATE()
        rocrate_tests_results = rocrate.execute_algorithm(resource, ticket)

        tests_results = self.integrate(fuji_tests_results, rocrate_tests_results)

        # Write the JSON-LD to a file
        output_file_results = f"C:\\Users\\egonzalez\\tests_results\\assessment-results-{ticket}.jsonld"
        with open(output_file_results, "w", encoding="utf-8") as f:
            json.dump(tests_results, f, ensure_ascii=False, indent=2)

    def integrate(self,test_results1, tests_results2):
        test1_members = test_results1.get("hadMember", [])
        test2_members = tests_results2.get("hadMember", [])

        test_results1["hadMember"] = test1_members + test2_members

        return test_results1

         
