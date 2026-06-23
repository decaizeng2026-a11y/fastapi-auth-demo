from fastapi import FastAPI,Depends,HTTPException,status
from pydantic import BaseModel
from auth import hash_password,verify_password,create_access_token,get_create_user
from database import fake_db,User
from sms import send_sms, generate_code, save_code, can_send, verify_code

app = FastAPI(title="Auth Demo")


# 请求体模型
# 用户注册模型
class Userregister(BaseModel):
    username:str
    password:str


# 用户登录模型
class UserLogin(BaseModel):
    username:str
    password:str


# 发送验证码模型
class SMSSend(BaseModel):
    phone: str


# 接收验证码模型
class SMSLogin(BaseModel):
    phone: str
    code: str


# 注册接口
@app.post("/register")
def register(user:Userregister):
    # 1.检查用户是否已存在
    if user.username in fake_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="用户已存在")
    # 2.密码加密
    hashed_pwd = hash_password(user.password)
    # 3.存入数据库
    fake_db[user.username] = User(
        username=user.username,
        hashed_password=hashed_pwd
    )
    return {"msg":"注册成功"}


# 登录接口
@app.post("/login")
def login(user:UserLogin):
    # 1.查询用户是否存在
    db_user = fake_db.get(user.username)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误"
        )

    # 2.验证密码
    if not verify_password(user.password,db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="用户名或密码错误")

    # 3.签发token
    access_token = create_access_token(data={"sub":user.username})
    return {"access_token":access_token,"token_type":"bearer"}


# 需要鉴权的接口
@app.get("/user/me")
def read_current_user(current_user:User = Depends(get_create_user)):
    return {
        "username":current_user.username,
        "created_at":current_user.created_at.isoformat()
    }


# 发送验证码
@app.post("/sms/send")
def sms_send(data:SMSSend):
    phone = data.phone
    if not can_send(phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="发送过于频繁，请60秒后再试"
        )
    code = generate_code()
    save_code(phone,code)
    send_sms(phone,code)
    return {"msg":"验证码已发送","expire_in":300}


# 验证码登录
@app.post("/sms/login")
def sms_login(data:SMSLogin):
    phone = data.phone
    code = data.code
    if not verify_code(phone,code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    if phone not in fake_db:
        fake_db[phone] = User(username=phone,hashed_password="")
    access_token = create_access_token(data={"sub":phone})
    return {"access_token":access_token,"token_type":"bearer"}


# 健康检查
@app.get("/health")
def health_chech():
    return {"status":"ok"}


