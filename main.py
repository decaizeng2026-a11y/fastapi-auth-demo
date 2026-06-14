from fastapi import FastAPI,Depends,HTTPException,status
from pydantic import BaseModel
from auth import hash_password,verify_password,create_access_token,get_create_user
from database import fake_db,User


app = FastAPI(title="Auth Demo")


# 请求体模型
class Userregister(BaseModel):
    username:str
    password:str

class UserLogin(BaseModel):
    username:str
    password:str

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

# 健康检查
@app.get("/health")
def health_chech():
    return {"status":"ok"}


