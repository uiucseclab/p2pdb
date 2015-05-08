# p2pdb client implementation
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA
import hashcash
import uuid
import socks
import socket
from json import dump, load
from os import remove
from base64 import b64decode


def create_connection(address, timeout=None, source_address=None):
    sock = socks.socksocket()
    sock.connect(address)
    return sock

socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', 9050)

# patch socket module with new create_connection
socket.socket = socks.socksocket
socket.create_connection = create_connection

from urllib2 import urlopen
from urllib import urlencode


def print_menu():
    print  "                            \033[1mp2pdb\033[0m                       \n"\
           "\033[4mMain menu\033[0m\n" \
           "    Commands:\n" \
           "        \033[4ml\033[0mist [\033[4mt\033[0mables|\033[4mr\033[0mecipients]\n" \
           "        \033[4ma\033[0mdd [\033[4mt\033[0mable_name=<table_key>|\033[4mr\033[0mecipient_name=<recipient_key>]\n" \
           "        \033[4mp\033[0mut <table_name> <recipient_name> <message>\n" \
           "        \033[4mg\033[0met [\033[4mt\033[0mable=<table> | \033[4mr\033[0mecipient=<recipient> | \033[4ms\033[0meconds_since=<seconds_since> | \033[4mb\033[0muckets=<bucket>]\n" \
           "        \033[4me\033[0mxit\n"


def write_tables(j):
    try:
        remove('tables.p2pdb')
    except OSError:
        pass
    tables = open('tables.p2pdb', 'w')
    dump(j, tables)
    tables.close()


def write_recipients(j):
    try:
        remove('recipients.p2pdb')
    except OSError:
        pass
    recipients = open('recipients.p2pdb', 'w')
    dump(j, recipients)
    recipients.close()


def read_tables():
    try:
        tables = open('tables.p2pdb', 'r')
    except IOError:
        print 'No tables yet!'
        return {}
    json = load(tables)
    tables.close()
    return json


def read_recipients():
    try:
        recipients = open('recipients.p2pdb', 'r')
    except IOError:
        print 'No recipients yet!'
        return {}
    json = load(recipients)
    recipients.close()
    return json


def add_command(c):
    try:
        a, v = c.split(' ')
    except ValueError:
        print 'Please only specify either a table or recipient.'
        return

    try:
        alot = v.split('=')
        target = alot[0]
        value = ''
        # account for equal signs in keys
        for part in alot[1:]:
            value += part
    except IndexError:
        print 'Please conform to the menu specification for the add command target.'
        return

    if target == '' or target is None:
        print 'No add target specified.'
        return
    if value == '' or value is None:
        print 'No add value specified.'
        return

    print 'Verifying key...'
    try:
        key = RSA.importKey(value)
    except (IndexError, ValueError):
        print 'Incorrect key format. Key not added.'
        return
    print 'Key verified.'

    if 'table' in target or target[0] == 't':
        json = read_tables()
        if target not in json:
            json[target] = key.exportKey('PEM')
            write_tables(json)
        else:
            print 'Key already in store.'
            return
    if 'recipient' in target or target[0] == 'r':
        json = read_recipients()
        if target not in json:
            json[target] = key.exportKey('PEM')
            write_recipients(json)
        else:
            print 'Key already in store.'
            return

    print 'Key added to store.'
    return


def list_command(c):
    try:
        l, t = c.split(' ')
    except ValueError:
        print 'Please only specify one "list" target'
        return

    view_keys = False
    if yes_no('View keys?') == 'y':
        view_keys = True

    if 'tables' in t or t[0] == 't':
        print 'Known tables:'
        j = read_tables()
        for k in j:
            print k
            if view_keys:
                print j[k]
        print '\n'
    elif 'recipients' in t or t[0] == 'r':
        print 'Known recipients:'
        j = read_recipients()
        for k in j:
            print k
            if view_keys:
                print j[k]
        print '\n'
    else:
        print 'Unknown "list" target, please try again.'
    return


def put_command(c):
    try:
        #p, t, r, m = c.split(' ')
        p = c.split(' ')
        t = p[1]
        r = p[2]
        # account for spaces in messages
        m = ''
        for word in p[3:]:
            m += word + ' '
    except IndexError:
        print 'Please execute the put command with all three arguments.'
        return

    mid = str(uuid.uuid4())
    print 'Message id: ' + mid

    json = read_tables()
    try:
        table_key = RSA.importKey(json[t])
    except KeyError:
        print 'No existing private key for table "' + t + '".'
        if yes_no('Did you wish to create a new key for that table?') == 'n':
            print 'Please add the key with the "add ' + t + '=<table_key>" command.'
            return
        table_key = RSA.generate(2048)
        print 'New table key: ' + table_key.exportKey('PEM')
        json[t] = table_key.exportKey('PEM')
        write_tables(json)

    json = read_recipients()
    try:
        recipient_key = RSA.importKey(json[r])
    except KeyError:
        print 'No existing private key for recipient "' + r + '".'
        if yes_no('Did you wish to create a new key for that recipient?') == 'n':
            print 'Please add the key with the "add ' + r + '=<recipient_key>" command.'
            return
        recipient_key = RSA.generate(2048)
        print 'New recipient key: ' + recipient_key.exportKey('PEM')
        json[r] = recipient_key.exportKey('PEM')
        write_recipients(json)

    cipher = PKCS1_OAEP.new(recipient_key)
    payload = cipher.encrypt(m).encode('base64')

    print 'Encrypted message: ' + payload

    print 'Proving work...'
    proof = SHA.new()
    table_pub = table_key.publickey().exportKey()
    recipient_pub = recipient_key.publickey().exportKey()
    proof.update((table_pub + payload).encode('UTF-8'))
    payload_hash = SHA.new(str(payload))
    signer = PKCS1_PSS.new(table_key)
    signature = signer.sign(payload_hash)
    data = {'table': table_pub,
            'proof': hashcash.make_cluster(str(table_pub + recipient_pub + payload), 21),
            'payload': payload,
            'to': recipient_pub,
            'payload_signature': signature.encode('base64')}
    url_data = urlencode(data)

    print 'Sending put request...'
    response = load(urlopen('http://hjc7rbogwpbbx7q4.onion:5000/put/' + mid, data=url_data))
    print ' - success: ' + str(response['success'])
    return


def get_command(c):
    g = c.split(' ')
    if len(c) < 2:
        print 'You must select at least one parameter for a get request.'
        return

    get_data = {}
    decrypt_key = None

    for p in g:
        if 'get' in p or p[0] == 'g':
            continue
        elif 'table' in p or p[0] == 't':
            try:
                p, table_name = p.split('=')
            except ValueError:
                print 'Incorrect format for the table name.'
                continue
            table_name = table_name.strip()

            json = read_tables()
            try:
                key = RSA.importKey(json[table_name])
            except (IndexError, ValueError):
                print 'Could not recreate table key.'
                continue

            get_data['tables'] = key.publickey().exportKey()

        elif 'recipient' in p or p[0] == 'r':
            try:
                p, recip_name = p.split('=')
            except ValueError:
                print 'Incorrect format for the recipient name.'
                continue
            recip_name = recip_name.strip()

            json = read_recipients()
            try:
                key = RSA.importKey(json[recip_name])
            except (IndexError, ValueError):
                print 'Could not recreate recipient key.'
                continue

            get_data['recipients'] = key.publickey().exportKey()
            decrypt_key = key

        elif 'seconds_since' in p or p[0] == 's':
            try:
                p, secs = p.split('=')
                secs = int(secs)
                secs = str(secs)
            except ValueError:
                print 'Incorrect format for the seconds_since. Please specify an integer.'
                continue

            get_data['seconds_since'] = secs

        elif 'bucket' in p or p[0] == 'b':
            try:
                p, bucket = p.split('=')
            except ValueError:
                print 'Incorrect format for the bucket.'
                continue

            get_data['bucket'] = bucket

        else:
            print 'Invalid get parameter "' + p + '."'
            continue
    if len(get_data) > 0:
        url_data = urlencode(get_data)
        print 'Sending get request...'
        response = load(urlopen('http://hjc7rbogwpbbx7q4.onion:5000/get/?' + url_data))
        print ' - success: ' + str(response['success'])
        if response['success']:
            print 'Number of messages: ' + str(len(response['entries']))

            if yes_no('View first message?') == 'n':
                print 'Returning to menu.'
                return

            for entry in response['entries']:
                print 'Message id: ' + entry['id']
                if decrypt_key is not None:
                    print 'Attempting to decrypt message text for given recipient...'
                    try:
                        cipher = PKCS1_OAEP.new(decrypt_key)
                        raw_cipher_text = b64decode(entry['payload'])
                        plaintext = cipher.decrypt(raw_cipher_text)
                        print 'Succeeded, message: ' + plaintext
                    except ValueError:
                        print 'Failed. Message must not be for that recipient!'

                    if yes_no('View next message?') == 'n':
                        print 'Returning to menu.'
                        return
                else:
                    print 'No decryption key for payload'
                    print 'Encrypted: ' + entry['payload']

                    if yes_no('View next message?') == 'n':
                        print 'Returning to menu.'
                        return
            print 'No more messages.'


def yes_no(prompt):
    yn = ''
    while yn != 'y' and yn != 'n':
        yn = raw_input(prompt + ' [y/n> ')
        yn = yn.strip()

    return yn


def process_command(c):
    if c == '' or c is None:
        print 'Please select a valid command.'
        return 0
    if 'add' in c or c[0] == 'a':
        add_command(c)
    elif 'list' in c or c[0] == 'l':
        list_command(c)
    elif 'put' in c or c[0] == 'p':
        put_command(c)
    elif 'get' in c or c[0] == 'g':
        get_command(c)
    elif 'exit' in c or c[0] == 'e':
        return -1
    else:
        print 'Please select a valid command.'
    raw_input('Press enter to continue...')
    return 0


def run():
    while 1:
        print_menu()
        c = raw_input('p2pdb> ')
        if process_command(c) < 0:
            break

if __name__ == '__main__':
    run()
