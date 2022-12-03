import os
import subprocess
from shutil import which, copy
import logging

scripts = [
  'app',
  'database',
  'membership_handling',
  'membership',
  'ocr',
  'sending',
  'settings',
  'utility',
  'views',
]

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logging.info('Started')

dir_path = os.path.dirname(os.path.realpath(__file__))
locales_path = os.path.join(dir_path, 'locales')

new_locale = input('Please enter a new locale you want to generate: ')

# Generate pot files if not existing
if not os.path.isdir(locales_path):
    logging.info('Generating locales directory ...')
    os.mkdir(locales_path)

# Generate initial pot files
logging.info('Generating initial pot files ...')
if which("pygettext3") is None:
    logging.error('pygettext3 command does not exists.')
    exit(1)
for script in scripts:
    if os.path.isfile(os.path.join(locales_path, f'{script}.pot')):
        continue
    logging.info('Generating %s.pot ...', script)
    result = subprocess.run(["pygettext3", "-d", script, "-o", os.path.join(locales_path, f"{script}.pot"), f"{script}.py"])
    if result.returncode != 0:
        logging.error('Failed to generate pot files.')
        exit(1)
logging.info('Initial pot files have been generated.')

# Generate new locale directory
locale_path = os.path.join(locales_path, new_locale)
lc_messages_path = os.path.join(locale_path, 'LC_MESSAGES')

if not os.path.isdir(lc_messages_path):
    os.makedirs(lc_messages_path)
    logging.info('New locale directory has been generated.')

# Copy pot files into new locale directory
logging.info('Generating po files ...')
for script in scripts:
    pot = f'{script}.pot'
    po = f'{script}.po'
    src_path = os.path.join(locales_path, pot)
    dest_path = os.path.join(lc_messages_path, po)
    if os.path.isfile(dest_path):
        continue
    logging.info('Copying %s to %s...', pot, po)
    copy(src_path, dest_path)
logging.info('po files have been generated.')

logging.info('Done')