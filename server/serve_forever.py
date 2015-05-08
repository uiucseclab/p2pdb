from flask import Flask, request, jsonify
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA
from flask.ext.sqlalchemy import SQLAlchemy
from models import *
from json import load
import hashcash, config, thread, time, requests, ast
import socks
import socket

def create_connection(address, timeout=None, source_address=None):
    sock = socks.socksocket()
    sock.connect(address)
    return sock

socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', 9050)

#patch socket module with new create_connection
socket.socket = socks.socksocket
socket.create_connection = create_connection

#now import patched urllib2
from urllib2 import urlopen, URLError
from urllib import urlencode

p2pdb = Flask('p2pdb_server')
p2pdb.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + config.DATABASE_PATH
db = SQLAlchemy(p2pdb)

@p2pdb.route('/put/<id>', methods = ['POST'])
def put(id):
    table = request.form.get('table')
    proof = request.form.get('proof')
    payload = request.form.get('payload')
    payload_signature = request.form.get('payload_signature')
    to_key = request.form.get('to')
    if (table is None or proof is None or payload is None or to_key is None or payload_signature is None):
        return jsonify(success = False, error = 'Missing POST parameters!  table, proof, payload, payload_signature, and to parameters required.'), 403
    proof_hash = SHA.new()
    proof_hash.update((table + payload))
    proof_hash = str(proof_hash.hexdigest())
    if (hashcash.verify_cluster(str(table + to_key + payload), str(proof)) != config.HASHCASH_BITS_REQUIRED):
        return jsonify(success = False, error = 'Proof of Work Invalid'), 403
    table_pub_key = RSA.importKey(table)
    payload_hash = SHA.new(str(payload))
    verifier = PKCS1_PSS.new(table_pub_key)
    if not table in config.ALLOWED_TABLES and config.ALLOWED_TABLES[0] != '*':
        return jsonify(success = False, error = 'This server not set to allow mirroring of this table.'), 403
    if not verifier.verify(payload_hash, payload_signature.decode('base64')):
        return jsonify(success = False, error = 'Payload must be signed with table key.'), 403
    message = Message(id, payload, proof, to_key, table)
    message.add_to_server_and_bucket()
    return jsonify(success = True)    
    
@p2pdb.route('/get/')
def get():
    ids = request.args.get('ids')
    seconds_since = request.args.get('seconds_since')
    tables = request.args.get('tables')
    recipients = request.args.get('recipients')
    bucket = request.args.get('bucket')
    query = Message.query
    if ids is None and seconds_since is None and tables is None and recipients is None and bucket is None:
        return jsonify(success = False, error = 'You must provide at least one filter to get entries.'), 403
    if ids is not None:
        ids = ','.split(ids)
        query = query.filter(~Message.id.in_(ids))
    if seconds_since is not None:
        seconds_since = int(seconds_since)
        query = query.filter(Message.time_received > int(time.time() - (seconds_since + 100)))
    if tables is not None:
        tables = ','.split(tables)
        query = query.filter(~Message.table.in_(tables))
    if recipients is not None:
        recipients = ','.split(recipients)
        query = query.filter(~Message.to.in_(recipients))
    if bucket is not None:
        bucket = int(bucket)
        query = query.filter_by(bucket_id=bucket)
    filtered_messages = []
    for message in query.all():
        filtered_messages.append(message.to_dict())
    return jsonify(success = True, entries = filtered_messages)

@p2pdb.route('/hello/')
def hello():    
    publish_routes = request.args.get('routes')
    supported_tables = request.args.get('tables')
    if publish_routes is not None and supported_tables is not None:
        server = Server.query.filter_by(routes = publish_routes).first()
        if server is None:
            server = Server(publish_routes, supported_tables)
            db.session.add(server)
            db.session.commit()
    server_list = []
    for server in Server.query.all():
        server_list.append((server.routes, server.tables))
    return jsonify(servers = server_list)

@p2pdb.route('/index/')
def index():
    returned_buckets = []
    for bucket in Bucket.query.filter_by(server_id = 1):
        if bucket.latest_hash is not None:
            returned_buckets.append((bucket.bucket_id, bucket.latest_hash))
    return jsonify(buckets = returned_buckets)

def update_server(server):
    try:
        server_route = ast.literal_eval(server.routes)['tor']
    except:
        print "Tor route not found for server " + str(server.routes)
        return
    if server.time_last_updated is None:
        # @todo - implement TOR
        #server_index = requests.get(server_route + "index/").json()
        server_index = load(urlopen(server_route + 'index/'))
        print server_index
        for bucket in server_index['buckets']:
            bucket_object = Bucket.query.filter_by(bucket_id = int(bucket[0])).first()
            hashes = Hash.query.filter_by(hash = bucket[1]).first()
            if hashes is None:
                #r = requests.get(server_route + 'get/', params = {'bucket' : int(bucket_object.bucket_id)}).json()
                params = urlencode({'bucket' : int(bucket_object.bucket_id)})
                r = load(urlopen(server_route + 'get/', data=params))
                print r
                for message in r['entries']:
                    message_object = Message.query.filter_by(payload = message['payload']).first()
                    if message_object is None:
                        message_object = Message(message['id'], message['payload'], message['proof'], message['to'], message['table'])
                        message_object.add_to_server_and_bucket()
                        db.session.add(message_object)
                        db.session.commit()
                hash = Hash(bucket[1])
                bucket_object.hashes.append(hash)
                db.session.commit()
    else:
        #r = requests.get(server_route + 'get/', params = {'seconds_since' : int(time.time() - server.time_last_updated) + 100}).json()
        params = urlencode({'seconds_since' : int(time.time() - server.time_last_updated) + 100})
        r = load(urlopen(server_route + 'get/', data=params))
        for message in r['entries']:
            message_object = Message.query.filter_by(payload = message['payload']).first()
            if message_object is None:
                message_object = Message(message['id'], message['payload'], message['proof'], message['to'], message['table'])
                message_object.add_to_server_and_bucket()
                db.session.add(message_object)
                db.session.commit()
    server.time_last_updated = int(time.time())
    db.session.commit()

def update_p2p():
    while True:
        payload = {'routes' : str(config.LOCATORS), 'tables' : (",".join(config.ALLOWED_TABLES))}
        servers = Server.query.filter(Server.id > 1).all()
        print servers
        for server in servers:
            # @todo - implement TOR
            try:
                #r = requests.get(ast.literal_eval(server.routes)['http'] + 'hello/', params = payload)
                params = urlencode(payload)
                r = load(urlopen(ast.literal_eval(server.routes)['tor'] + 'hello/', data=params))
            except AttributeError as e:
                print e
                continue
            except URLError:
                print "Network error on host", server.routes
                continue
            #json_response = r.json()
            json_response = r
            for new_server in json_response['servers']:
                server_route = new_server[0]
                potential_server = Server.query.filter_by(routes = server_route).first()
                if potential_server is None:
                    potential_server = Server(server_route, new_server[1])
                    db.session.add(potential_server)
                    db.session.commit()
            update_server(server)
            print str(server.routes), "updated"
        time.sleep(30)

if __name__ == '__main__':
    host = '127.0.0.1' if config.LISTEN_GLOBALLY else None
    #thread.start_new_thread(update_p2p, ())

    p2pdb.run(host=host, port=config.LISTEN_PORT, debug=config.DEBUG)
