== What is this? ==

p2pdb server is a peer-to-peer database engine built to operate over multiple protocols
and provide varying levels of security to a new generation of distributed applications.

p2pdb treats database tables and users as RSA keys.  A p2pdb server can mirror a certain
set of tables, or all tables.  Each message that comes in must be signed with the table
into which it is inserted, and must come with a hashcash proof-of-work (21-bit SHA cluster PoW).
Messages are encrypted with the RSA key of the recipient, and cannot be read by the server.

It is easy to control the permissions of any database entry - simply distribute the key only to
those to whom you want to grant access.  Public channels correspond to openly distributed private keys,
which can be hardcoded into applications

The aim of p2pdb is not to attempt to provide massively scaleable guarantees - eventually, we aim to support
ten to fifty million entries per p2pdb server efficiently.  We believe that this is enough for the requirements
of most distributed web applications.  Rather, p2pdb focuses on providing a simple-to-use interface and trivial
integration with existing distributed and web applications.  p2pdb also focuses on the simplicity of its 
protocol and data structures, believing that a well designed project is one that can be understood right away.

p2p builds exclusively on existing and tested technology, including RSA, Flask and SQLAlchemy, and
leverages the existing, popular, and portable HTTP protocol for all communications.  Thus, it can
be made to run on any device with sufficient resources that supports HTTP.

== Installation ==

First, install a Python 2.x interpreter and python-dev (the C python headers, required for pycrypto).  Then, simply:

1. python virtualenv.py server
2. . server/bin/activate
3. pip install flask pycrypto flask-sqlalchemy requests
4. vi config.py
5. python db_create.py
6. python serve_forever.py

== Current Limitations ==

1. TOR support not yet integrated.
2. Table whitelist and integration with hello (only return servers that support req'd table)
3. Speed in several aspects - index generation (can easily cache), bucket hash updates (should be threaded)
4. Server routes cannot be changed as they are currently unique server ID's.  Eventually - key based server ID's
5. Not tested on large applications or with database backends other than SQLite (though SQLAlchemy should support MySQL, etc)

== Testing Server ==

See test_server.py for a simple test script to post a message.  You can then retrieve the message by sending a GET request to
[p2pdb URL]/get/?seconds_since=10000 (to get all messages in the last 10000 seconds, for other parameters see "Technical Information")

== Client Implementations ==

We provide a sample client implementation in the client/ folder of this Github repository.  The client implementation
is designed to implement with distributed Python applications, which can easily be based on Django or Flask (simply
replace the database layer with p2pdb and distribute the application for running client-side). (COMING SOON)

== Technical Information, Protocol Info, and Overview ==

For an overview of the theoretical ideas that p2pdb implements, please see the slides at the root of this
GitHub repository in overview.pdf (COMING SOON - by Thursday night).

