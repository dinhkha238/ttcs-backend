from pydantic import BaseModel, Field


class Customer(BaseModel):
    fullname : str = Field(...)
    user : str = Field(...)
    password : str = Field(...)

class Login(BaseModel):
    user : str = Field(...)
    password : str = Field(...)

class Cart(BaseModel):
    id : str = Field(...)
    name : str = Field(...)
    price : int = Field(...)

class Product(BaseModel):
    name : str = Field(...)
    color : str = Field(...)
    price : int = Field(...)
    urlImg : str = Field(...)

class Order(BaseModel):
    name : str = Field(...)
    id_user : str = Field(...)
    user: str = Field(...)
    time: str = Field(...)
    address : str = Field(...)
    phone : str = Field(...)
    products : list = Field(...)
    total : int = Field(...)
    note : str = Field(...)

def ResponseModel(data, message):
    return {
        "data": [data],
        "code": 200,
        "message": message,
    }