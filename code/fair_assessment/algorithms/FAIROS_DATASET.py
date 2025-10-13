import logging
from FAIROS_DATASET_FUJI import FAIROS_DATASET_FUJI

logger = logging.getLogger(__name__)

class FAIROS_DATASET:
    def execute_algorithm(self, resource, ticket):
        logger.info("Executing tests on dataset")

        fuji = FAIROS_DATASET_FUJI()
        fuji.execute_algorithm(resource,ticket)
