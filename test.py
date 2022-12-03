import logging
from utility import Utility

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logging.info("Started")

Utility.generate_translation_files()