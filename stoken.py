from itsdangerous import URLSafeTimedSerializer
from keys import salt

def encode(data):
    serializer=URLSafeTimedSerializer('code@123')
    return serializer.dumps(data,salt=salt)

def decode(data):
    serializer=URLSafeTimedSerializer('code@123')
    return serializer.loads(data,salt=salt)
