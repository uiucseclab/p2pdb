from sqlalchemy import Column, Integer, String, ForeignKey
from serve_forever import db
import config, md5, time, thread

class Message(db.Model):
    __tablename__ = 'messages'
    serverside_id = Column(Integer, primary_key=True, autoincrement=True)
    time_received = Column(Integer, unique=False)
    id = Column(String(300), unique=False)
    payload = Column(String(10000), unique=True)
    proof = Column(String(100), unique=False)
    to = Column(String(300), unique=False)
    table = Column(String(300), unique=False)
    bucket_id = Column(Integer)
    bucket_server_id = Column(Integer, ForeignKey('buckets.id'))
    server_id = Column(Integer, ForeignKey('servers.id'))
    

    def __init__(self, id, payload, proof, to, table):
        self.id = id
        self.payload = payload
        self.proof = proof
        self.to = to
        self.table = table
        self.time_received = int(time.time())

    def add_to_server_and_bucket(self):
        server = Server.query.filter_by(id = 1).first()
        server.messages.append(self)
        m = md5.new()
        m.update(self.payload)
        bucket = int(m.hexdigest(), 16) % config.NUM_BUCKETS
        bucket_obj = Bucket.query.filter_by(bucket_id = bucket).first()
        bucket_obj.messages.append(self)
        self.bucket_id = bucket_obj.bucket_id            
        db.session.add(self)
        db.session.add(bucket_obj)
        db.session.commit()
        bucket_obj.update_hash()

    def to_dict(self):
        return {'id' : self.id, 'time_received' : self.time_received, 'payload': self.payload,
                'proof' : self.proof, 'to': self.to, 'table': self.table, 'bucket_id' : self.bucket_id }

class Hash(db.Model):
    __tablename__ = 'hashes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    hash = Column(String(300), unique=False)
    bucket_id = Column(Integer, ForeignKey('buckets.id'))

    def __init__(self, hash):
        self.hash = hash

class Bucket(db.Model):
    __tablename__ = 'buckets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    bucket_id = Column(Integer)
    messages = db.relationship('Message', backref='bucket', lazy='dynamic')
    latest_hash = Column(String)
    hashes = db.relationship('Hash', backref='bucket', lazy='dynamic')
    server_id = Column(Integer, ForeignKey('servers.id'))

    def __init__(self, bucket_id):
        self.bucket_id = bucket_id 

    def update_hash(self):
        ordered_messages = self.messages.order_by(Message.id).all()
        if len(ordered_messages) == 0:
            return
        m = md5.new()
        for message in ordered_messages:
            m.update(message.id)
        current_hash = m.hexdigest()
        if current_hash != self.latest_hash:
            self.latest_hash = current_hash
            self.hashes.append(Hash(m.hexdigest()))
            db.session.add(self)
            db.session.commit()

class Server(db.Model):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    time_last_updated = Column(Integer, unique=False)
    routes = Column(String(10000), unique=False)
    tables = Column(String(10000), unique=False)
    buckets = db.relationship('Bucket', backref='server', lazy='dynamic')
    messages = db.relationship('Message', backref='server', lazy='dynamic')
    
    def __init__(self, routes, supported_tables):
        self.routes = routes
        for i in range(0, config.NUM_BUCKETS):
            self.buckets.append(Bucket(i))
        self.tables = supported_tables
