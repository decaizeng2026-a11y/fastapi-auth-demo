from datetime import datetime

fake_db = {}

class User:
    def __init__(self,username:str,hashed_password:str):
        self.username = username
        self.hashed_password = hashed_password
        self.created_at = datetime.utcnow()