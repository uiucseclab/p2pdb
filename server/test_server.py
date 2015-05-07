import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA
import hashcash, uuid
import socks
import socket
from json import load

def create_connection(address, timeout=None, source_address=None):
    sock = socks.socksocket()
    sock.connect(address)
    return sock

socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', 9050)

#patch socket module with new create_connection
socket.socket = socks.socksocket
socket.create_connection = create_connection

from urllib2 import urlopen
from urllib import urlencode

id = str(uuid.uuid4())
print 'Message ID:', id
key = RSA.generate(2048)
print 'Table Key:', key.exportKey()
table = key.publickey().exportKey()
print 'Table Pub Key:', table
payload = '!!@what the fudge'
recipient_key = RSA.generate(2048)
print 'Recipient Key:', recipient_key.exportKey()
recipient = recipient_key.publickey().exportKey()
print 'Recipient Pub Key:', recipient
cipher = PKCS1_OAEP.new(recipient_key)
print 'Payload: ', payload
payload = cipher.encrypt(payload).encode('base64')
print 'Encrypted Payload: ', payload
proof = SHA.new()
proof.update((table + payload).encode('UTF-8'))
payload_hash = SHA.new(str(payload))
signer = PKCS1_PSS.new(key)
signature = signer.sign(payload_hash)
print 'Payload hash', payload_hash.hexdigest()
#r = requests.post('http://127.0.0.1:5000/put/' + id, data = {'table': table, 'proof': hashcash.make_cluster(str(table + recipient + payload), 21), 'payload': payload, 'to': recipient, 'payload_signature': signature.encode('base64')})
data = {'table': table, 'proof': hashcash.make_cluster(str(table + recipient + payload), 21), 'payload': payload, 'to': recipient, 'payload_signature': signature.encode('base64')}
urldata = urlencode(data)

r = load(urlopen('http://hjc7rbogwpbbx7q4.onion:5000/put/' + id, data=urldata))
print r

get_data = {
    'table': key.exportKey(),
    'recipient': recipient_key.exportKey(),
}

data = urlencode(get_data)
url = 'http://hjc7rbogwpbbx7q4.onion:5000/get/'
print "Url: " + url
print 'Data: ' + data
r = load(urlopen(url, data=data))

print r

#print r.text