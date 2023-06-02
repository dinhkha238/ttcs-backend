from datetime import datetime, timedelta
from typing import Union, Any
import jwt

SECURITY_ALGORITHM = 'HS256'
SECRET_KEY = '123456'


def generate_token(id: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(
        seconds=60*60*24   # Expired after 1 hours
    )
    to_encode = {   
        "exp": expire, "_id": id
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=SECURITY_ALGORITHM)
    return encoded_jwt