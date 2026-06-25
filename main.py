from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from auth import hash_password, verify_password, create_access_token, get_create_user
from database import fake_db, User
from sms import send_sms, generate_code, save_code, can_send, verify_code
from obs import get_upload_url, get_file_url, delete_file
from middleware import RequestLogMiddleware


app = FastAPI(title="Auth Demo")
app.add_middleware(RequestLogMiddleware)


# 请求体模型
# 用户注册模型
class Userregister(BaseModel):
    username: str
    password: str


# 用户登录模型
class UserLogin(BaseModel):
    username: str
    password: str


# 发送验证码模型
class SMSSend(BaseModel):
    phone: str


# 接收验证码模型
class SMSLogin(BaseModel):
    phone: str
    code: str


# 上传文件模型
class UploadRequest(BaseModel):
    filename: str


# 上传文件url
class UploadCallback(BaseModel):
    object_key: str


# --------JWT鉴权----------
# 注册接口
@app.post("/register")
def register(user: Userregister):
    # 1.检查用户是否已存在
    if user.username in fake_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    # 2.密码加密
    hashed_pwd = hash_password(user.password)
    # 3.存入数据库
    fake_db[user.username] = User(
        username=user.username,
        hashed_password=hashed_pwd
    )
    return {"msg": "注册成功"}


# 登录接口
@app.post("/login")
def login(user: UserLogin):
    # 1.查询用户是否存在
    db_user = fake_db.get(user.username)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误"
        )

    # 2.验证密码
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名或密码错误")

    # 3.签发token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# 需要鉴权的接口
@app.get("/user/me")
def read_current_user(current_user: User = Depends(get_create_user)):
    return {
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat()
    }


# -------短信模块-------
# 发送验证码
@app.post("/sms/send")
def sms_send(data: SMSSend):
    phone = data.phone
    if not can_send(phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="发送过于频繁，请60秒后再试"
        )
    code = generate_code()
    save_code(phone, code)
    send_sms(phone, code)
    return {"msg": "验证码已发送", "expire_in": 300}


# 验证码登录
@app.post("/sms/login")
def sms_login(data: SMSLogin):
    phone = data.phone
    code = data.code
    if not verify_code(phone, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    if phone not in fake_db:
        fake_db[phone] = User(username=phone, hashed_password="")
    access_token = create_access_token(data={"sub": phone})
    return {"access_token": access_token, "token_type": "bearer"}


# ------------文件上传模块-------------
@app.post("/upload/avatar")
# 头像上传函数
def request_upload(
        # 接收文件名
        request: UploadRequest,
        # 通过依赖注入获取用户信息
        current_user: User = Depends(get_create_user)
):
    """
    请求上传头像，返回预签名URL
    前端拿到URL后直接上传到OBS
    """
    # 调用get_upload_url函数 将用户唯一信息和文件名传入进去生成一个唯一的文件名和预签名
    upload_info = get_upload_url(current_user.username, request.filename)
    # 上传成功后返回预签名地址，文件名，预签名地址过期时间
    return {
        "msg": "获取上传地址成功",
        "upload_url": upload_info["upload_url"],
        "object_key": upload_info["object_key"],
        "expires_in": upload_info["expires_in"]
    }


@app.post("/upload/callback")
# 回调函数，传入前端返回的唯一文件名，通过依赖注入拿到用户信息
def upload_callback(data: UploadCallback, current_user: User = Depends(get_create_user)):
    """
    前端上传成功后回调，更新数据库里面的头像字段
    如果有旧头像，用于后续删除
    """
    # 模拟：记录用户旧头像，用于后续删除
    # 设置一个空值
    old_avatar = None
    # 判断用户数据库里面有没有avatar_key字段，有就代表之前上传过头像
    if hasattr(current_user, 'avatar_key'):
        # 如果有就将旧头像复赋值old_avatar
        old_avatar = current_user.avatar_key

    # 更新用户头像Key，将前端传回的key传给后端写入数据库
    current_user.avatar_key = data.object_key

    # 异步删除旧头像（真实环境用celery或后台线程）
    if old_avatar:
        print(f"[模拟异步]删除旧头像：{old_avatar}")
        delete_file(old_avatar)

    # 调用get_file_url返回查看文件地址
    avater_url = get_file_url(data.object_key)
    return {
        "msg": "头像更新成功",
        "avatar_url": avater_url
    }


@app.get("/user/profile")
# 获取用户信息接口，通过依赖注入获取用户信息
def get_user_profile(current_user: User = Depends(get_create_user)):
    """获取用户完整信息，包括头像"""
    # 头像url默认为空
    avatar_url = None
    # 判断是否上传过头像以及头像里面是否有数据
    if hasattr(current_user, 'avatar_key') and current_user.avatar_key:
        # 调用get_file_url函数生成查看url
        avatar_url = get_file_url(current_user.avatar_key)

        # 返回用户信息
        return {
            "username": current_user.username,
            "created_at": current_user.created_at.isoformat(),
            "avatar_url": avatar_url
        }


# 健康检查
@app.get("/health")
def health_chech():
    return {"status": "ok"}
