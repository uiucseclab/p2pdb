# p2pdb server config
# WARNING: Server is not guaranteed to be completely secure
# Run only in a sandbox or virtual machine with no sensitive files or data

# Port to listen on (default 5000)
LISTEN_PORT = 5000

# Listen for external traffic.  We recommend setting to True for performance
# increases when synchronizing with other servers
LISTEN_GLOBALLY = True

# Dictionary of transport methods to resource locator for server root
# Any transport protocol supporting HTTP can be used, but current clients
# support only url and tor as keys for standard URL and .onion resource
# locatiors
LOCATORS = { 'http': 'http://suryathe.chickenkiller.com:5000/',
    'tor' : 'http://example.onion'
}

# List of table keys allowed to be mirrored on this database
# Default (single entry of '*') means all tables can be stored
ALLOWED_TABLES = [ '*' ]

# Absolute path to messages SQLite database file (can also use SQL)
DATABASE_PATH = 'messages.db'

# WARNING: DRAGONS AHEAD.  DEVELOPER CONFIGURATION.
# DO NOT EDIT ANYTHING BELOW THIS LINE WITHOUT GOOD REASON.
# YOU RUN THE RISK OF BECOMING DESYNCHRONIZED WITH THE NETWORK
# ---------------------------------------------------------
HASHCASH_BITS_REQUIRED = 21
NUM_BUCKETS = 50000
DEBUG = False
