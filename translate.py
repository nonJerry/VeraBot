from typing import Callable
import logging
import os
import glob
import subprocess
from shutil import which
import gettext

class Translate:


    @staticmethod
    def get_translation_function(namespace: str) -> Callable[[str], str]:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        locales_path = os.path.join(dir_path, 'locales')
        if not os.path.isdir(locales_path):
            logging.error('Locales directory does not exist. Please use generate_locales.py to generate it first.')
            exit(1)
        translate = gettext.translation('app', locales_path, fallback=True)
        return translate.gettext
    
    @staticmethod
    def generate_translation_files() -> None:
        logging.info('Generating translation files ...')
        dir_path = os.path.dirname(os.path.realpath(__file__))
        locales_path = os.path.join(dir_path, 'locales')
        if which("msgfmt") is None:
            logging.error('msgfmt command does not exists.')
            exit(1)
        elif not os.path.isdir(locales_path):
            logging.error('Locales directory does not exist. Please use generate_locales.py to generate it first.')
            exit(1)

        for entry in os.listdir(locales_path):
            entry_path = os.path.join(locales_path, entry)
            if not os.path.isdir(entry_path):
                continue
            lc_messages_path = os.path.join(entry_path, 'LC_MESSAGES')
            if not os.path.isdir(locales_path):
                logging.error('LC_MESSAGES directory does not exist. Please use generate_locales.py to generate it first.')
                exit(1)
            for po in glob.glob(f'{lc_messages_path}/*.po'):
                mo = po.split('.')[0] + '.mo'
                po_path = os.path.join(lc_messages_path, po)
                mo_path = os.path.join(lc_messages_path, mo)
                if os.path.isfile(mo_path):
                    continue
                logging.info('Generating %s/LC_MESSAGES/%s ...', entry, mo)
                result = subprocess.run(["msgfmt", "-o", mo_path, po_path])
                if result.returncode != 0:
                    logging.error('Failed to generate %s.', mo)
                    exit(1)
                
        logging.info('Translation files are generated.')
        return
    