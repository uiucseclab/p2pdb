import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA
import hashcash, uuid

id = str(uuid.uuid4())
print 'Message ID:', id
key = RSA.generate(2048)
print 'Table Key:', key.exportKey()
table = key.publickey().exportKey()
print 'Table Pub Key:', table
payload = '!!@what the fak'
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
r = requests.post('http://suryathe.chickenkiller.com:5000/put/' + id, data = {'table': table, 'proof': hashcash.make_cluster(str(table + recipient + payload), 21), 'payload': payload, 'to': recipient, 'payload_signature': signature.encode('base64')})

print r.text
