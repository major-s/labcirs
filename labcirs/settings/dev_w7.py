from .dev import *

# Test settings
# Chose browser for testing. May be Firefox or Chrome
BROWSER = 'Chrome'
CHROME_DRIVER = join_path(BASE_DIR,
                          'functional_tests/chromedriver/chromedriver.exe')