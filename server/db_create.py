from models import db, Server
import config

db.create_all()
s = Server(str(config.LOCATORS), ",".join(config.ALLOWED_TABLES))
db.session.add(s)
db.session.commit()
