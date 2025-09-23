import logging
import traceback
from rocrate.rocrate import ROCrate
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from FAIROS_DATASET import FAIROS_DATASET

logger = logging.getLogger(__name__)

class FAIROS:


    def execute_algorithm(rocrate_filename, ticket):
        logging.info(f"Exploring rocrate file {rocrate_filename}")

        try:
            rocrate = ROCrate(rocrate_filename)
            ro = rocrate.dereference("./").as_jsonld()  # ro itself
            ro_parts = [
                rocrate.dereference(part["@id"]).as_jsonld()
                for part in ro["hasPart"]
            ]
            logging.info(f"{len(ro_parts)} resources detected in the RO")
            for element in ro_parts:
                type = element["@type"]
                id = element["@id"]   
                if ("Dataset" in type and not "http://purl.org/wf4ever/wf4ever#Folder" in type) or "http://purl.org/wf4ever/wf4ever#Dataset" in type:   
                    logger.info(f"Resource detected as Dataset: {id}")
                    dataset = FAIROS_DATASET()
                    dataset.execute_algorithm(element, ticket)

        except Exception as ex:
            logger.error("Error to load rocrate file")
            print(traceback.format_exc())
        

    def get_id():
        return "FAIROS"
    def getTTL():
        return "simple"
    