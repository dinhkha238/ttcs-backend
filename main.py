from bson import ObjectId
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request,status
from pymongo import MongoClient
from fastapi.responses import JSONResponse
import uvicorn
from model import Customer, Login, Order, Product
from fastapi.middleware.cors import CORSMiddleware
from security import validate_token
from services import generate_token
import datetime
app = FastAPI(
        docs_url="/api/docs",
        openapi_url="/api/docs/openapi.json",
        redoc_url=None
    )
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Connect to MongoDB
client = MongoClient("mongodb://20.243.123.180:27017/")
db = client["shopping"]
db_customer = db["customers"]
db_products = db["products"]
db_orders = db["orders"]
db_sessions = db["sessions"]

router = APIRouter(prefix="/api")

@router.get("/")
def get_customers():
    # In ra tài liệu
    documents = db_customer.find()
    customer_list= []
    for doc in documents:
        customer_list.append(customer_info(doc))
    return customer_list

@router.get("/get-customer/",dependencies=[Depends(validate_token)])
async def get_customer(id:str = Depends(validate_token)):
    customer = db_customer.find_one({"_id": ObjectId(id)})
    if customer:
        return customer_info(customer)
    raise HTTPException(status_code=404, detail=f"Customer {id} not found")


@router.post("/create-customer")
async def create_customer(customer:Customer = Body(...)):
    customer = customer.dict()
    existing_user = db_customer.find_one({"user": customer["user"]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exist"
        )
    db_customer.insert_one(customer_created(customer))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Account created successfully."},
    ) 

@router.post("/login")
async def check_customer(request: Request,body:Login = Body(...)):
    body = body.dict()
    existing_user = db_customer.find_one({"user": body["user"],"password": body["password"]})
    if existing_user:
        token = generate_token(str(existing_user['_id']))
        # Lấy thông tin về địa chỉ IP và thời gian kết nối
        ip = request.client.host
        time = datetime.datetime.now()
        
        # Lưu thông tin vào cơ sở dữ liệu
        db_sessions.insert_one({
            "user": existing_user['user'],
            "ip": ip,
            "time": time
        })
        # Trả về JWT 
        return {'token': token}

    # Nếu thông tin đăng nhập không hợp lệ, trả về lỗi 401 Unauthorized
    raise HTTPException(status_code=401, detail='Đăng nhập không thành công')
      

@router.get("/get-products/{option}")
async def get_products(
    option: str,
    filter: str = "",
    sort: str = "",
):
    documents = db_products.find()
    product_list= []
    if option == "All":
        for doc in documents:
            if filter.lower() in doc["color"].lower() :
                    product_list.append(product_info(doc))
        if(sort == "option2"):
            product_list.sort(key=lambda x: x['color'])
            return product_list
        elif(sort == "option3"):
            product_list.sort(key=lambda x: x['price'])
            return product_list
        elif(sort == "option4"):
            product_list.sort(key=lambda x: x['price'],reverse=True)
            return product_list
        return product_list
    else:
        for doc in documents:
            if doc["name"] == option and filter.lower()  in doc["color"].lower() :
                product_list.append(product_info(doc))
        if(sort == "option2"):
            product_list.sort(key=lambda x: x['color'])
            return product_list
        elif(sort == "option3"):
            product_list.sort(key=lambda x: x['price'])
            return product_list
        elif(sort == "option4"):
            product_list.sort(key=lambda x: x['price'],reverse=True)
            return product_list
        return product_list

@router.put("/add-to-cart/{id}",dependencies=[Depends(validate_token)])
async def add_to_cart(
    id: str,
    idUser:str =  Depends(validate_token)
):
    product = db_products.find_one({"_id": ObjectId(id)})
    info_user = db_customer.find_one({"_id": ObjectId(idUser)})
    user = db_customer.find_one({"_id": ObjectId(idUser),"cart.data._id": id})

    if user:
        db_customer.update_one({"_id": ObjectId(idUser),"cart.data._id": id}, {"$inc": {"cart.data.$.count":1 }})

    else:
        db_customer.update_one({"_id": ObjectId(idUser)}, {"$push": {"cart.data":crud_product_info(product) }})
    db_customer.update_one({"_id": ObjectId(idUser)}, {"$inc": {"cart.total": product["price"] }})

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Add to cart successfully."}
    )

@router.delete("/delete-cart/{id}",dependencies=[Depends(validate_token)])
async def delete_cart(
    id: str,
    idUser:str =  Depends(validate_token)
):
    product = db_customer.find_one({"_id": ObjectId(idUser),"cart.data._id": id})
    for item in product['cart']['data']:
        if item['_id'] == id:
            db_customer.update_one({"_id": ObjectId(idUser)}, {"$pull": {"cart.data":item}})
            db_customer.update_one({"_id": ObjectId(idUser)}, {"$inc": {"cart.total": -item["price"]*item["count"] }})

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Delete cart successfully."}
    )
@router.delete("/delete-all-cart",dependencies=[Depends(validate_token)])
async def delete_all_cart(
    idUser:str =  Depends(validate_token)
):
    db_customer.update_one({"_id": ObjectId(idUser)}, {"$set": {"cart.data":[]}})
    db_customer.update_one({"_id": ObjectId(idUser)}, {"$set": {"cart.total":0}})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Delete all cart successfully."}
    )

@router.put("/decrease-product/{id}",dependencies=[Depends(validate_token)])
async def decrease_product(
    id: str,
    idUser:str =  Depends(validate_token)
):
    product = db_customer.find_one({"_id": ObjectId(idUser),"cart.data._id": id})
    for item in product['cart']['data']:
        if item['_id'] == id:
            if item["count"] > 1:
                db_customer.update_one({"_id": ObjectId(idUser),"cart.data._id": id}, {"$inc": {"cart.data.$.count":-1 }})
                db_customer.update_one({"_id": ObjectId(idUser)}, {"$inc": {"cart.total": -item["price"] }})
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"message": "Decrease product successfully."}
                )

    
@router.post("/create-product")
async def create_product(product:Product = Body(...)):
    product = product.dict()
    existing_product = db_products.find_one({"color": product["color"]})
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Product already exist"
        )
    key_news = db_products.count_documents({})+1
    product["key"] = str(key_news) 
    db_products.insert_one(product)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Product created successfully."},
    )
    
@router.put("/update-product/{id}")
async def update_product(
    id: str,
    product:Product = Body(...),
):
    product = product.dict()
    db_products.update_one({"_id": ObjectId(id)}, {"$set": product})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Product updated successfully."},
    )
@router.delete("/delete-product/{id}")
async def delete_product(
    id: str,
):
    db_products.delete_one({"_id": ObjectId(id)})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Product deleted successfully."},
    )
    
@router.put("/update-customer/{id}")
async def update_customer(
    id: str,
    customer:Customer = Body(...),
):
    customer = customer.dict()
    db_customer.update_one({"_id": ObjectId(id)}, {"$set": customer})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Customer updated successfully."},
    )
@router.delete("/delete-customer/{id}")
async def delete_customer(
    id: str,
):
    db_customer.delete_one({"_id": ObjectId(id)})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Customer deleted successfully."},
    )

@router.post("/create-order")
async def add_order(
    order:Order = Body(...),

):
    order = order.dict()
    db_orders.insert_one(order)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Order created successfully."},
    )
@router.get("/get-orders")
async def get_orders(
    month_year:str = "all",
):
    documents = db_orders.find()
    order_list= []
    if month_year == "all":
        for doc in documents:
            order_list.append(order_info(doc))
        return order_list
    else:
        for doc in documents:
            time = doc['time'].split(" ")[0]
            date_obj = datetime.strptime(month_year, "%Y-%m")
            formatted_date = date_obj.strftime("%m/%Y")
            if formatted_date in time:
                order_list.append(order_info(doc))
        return order_list
@router.get("/get-orders-by-id",dependencies=[Depends(validate_token)])
async def get_orders_by_id(
    idUser:str =  Depends(validate_token)
):
    documents = db_orders.find({"id_user":idUser})
    order_list= []
    for doc in documents:
        order_list.append(order_info(doc))
    return order_list
@router.delete("/delete-order/{id}")    
async def delete_order(
    id: str,
):
    db_orders.delete_one({"_id": ObjectId(id)})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Order deleted successfully."},
    )

# Mount the router in your main FastAPI application
app.include_router(router)

    
def order_info(order) -> dict:
    return {
        "_id":str(order["_id"]),
        "id_user": order["id_user"],
        "user": order["user"],
        "name": order["name"],
        "time": order["time"],
        "address": order["address"],
        "phone": order["phone"],
        "products": order["products"],
        "total": order["total"],
        "note": order["note"],
    }
def crud_product_info(product) -> dict:
    return {
        "_id":str(product["_id"]),
        "key": product["key"],
        "name": product["name"],
        "color": product["color"],
        "price": product["price"],
        "urlImg":product["urlImg"],
        "count": 1,
    }



def product_info(product) -> dict:
    return {
        "_id":str(product["_id"]),
        "key": product["key"],
        "name": product["name"],
        "color": product["color"],
        "price": product["price"],
        "urlImg":product["urlImg"],
        # "count": product["count"],
    }

    

def customer_created(customer) -> dict:
    return {
        "fullname": customer["fullname"],
        "user": customer["user"],
        "password": customer["password"],
        "cart": {
            "data":[],
            "total":0
        },
        
    }
def customer_info(customer) -> dict:
    return {
        "id": str(customer["_id"]),
        "fullname": customer["fullname"],
        "user": customer["user"],
        "password": customer["password"],
        "cart": customer["cart"] 
    }



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)