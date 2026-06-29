from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from auth import hash_password, verify_password, create_access_token, get_current_user
from database import get_db
from crud import create_user, get_user_by_username, get_user_by_phone, update_user_avatar
from sms import send_sms, generate_code, save_code, can_send, verify_code
from obs import get_upload_url, get_file_url, delete_file
from middleware import RequestLogMiddleware
from logger import logger, get_request_id
from crud import create_order
from tasks import open_blind_box
from celery_app import celery_app


app = FastAPI(title="Auth Demo")
app.add_middleware(RequestLogMiddleware)


# ==============pydantic模型=====================
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
def register(user: Userregister, db: Session = Depends(get_db)):
    # 1.检查用户是否已存在
    if get_user_by_username(db, user.username):
        logger.bind(get_request_id=get_request_id()).warning(f"注册失败：用户名{user.username}已存在")
        raise HTTPException(status_code=400, detail="用户已存在")
    # 2.密码加密
    hashed_pwd = hash_password(user.password)
    # 3.存入数据库
    db_user = create_user(db, user.username, hashed_pwd)
    logger.bind(request_id=get_request_id()).info(f"用户注册成功：{user.username},ID={db_user.id}")
    return {"msg": "注册成功", "usser_id": db_user.id}


# ==================== 登录 ====================
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        logger.bind(request_id=get_request_id()).warning(f"登录失败：用户名 {user.username} 密码错误或用户不存在")
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    access_token = create_access_token(data={"sub": user.username})
    logger.bind(request_id=get_request_id()).info(f"用户登录成功: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


# ==================== 短信发送 ====================
@app.post("/sms/send")
def sms_send(data: SMSSend):
    phone = data.phone
    if not can_send(phone):
        logger.bind(request_id=get_request_id()).warning(f"短信发送被拦截（频控）: {phone}")
        raise HTTPException(status_code=429, detail="发送过于频繁，请60秒后再试")
    code = generate_code()
    save_code(phone, code)
    send_sms(phone, code)
    logger.bind(request_id=get_request_id()).info(f"短信验证码已发送: {phone}")
    return {"msg": "验证码已发送", "expire_in": 300}


# ==================== 短信登录 ====================
@app.post("/sms/login")
def sms_login(data: SMSLogin, db: Session = Depends(get_db)):
    if not verify_code(data.phone, data.code):
        logger.bind(request_id=get_request_id()).warning(f"短信登录失败（验证码错误）: {data.phone}")
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = get_user_by_phone(db, data.phone)
    if not user:
        user = create_user(db, username=data.phone, hashed_password="", phone=data.phone)
        logger.bind(request_id=get_request_id()).info(f"新用户短信注册成功: {data.phone}")

    access_token = create_access_token(data={"sub": data.phone})
    logger.bind(request_id=get_request_id()).info(f"短信登录成功: {data.phone}")
    return {"access_token": access_token, "token_type": "bearer"}


# ==================== 文件上传 ====================
@app.post("/upload/avatar")
def request_upload(request: UploadRequest, current_user=Depends(get_current_user)):
    upload_info = get_upload_url(current_user.username, request.filename)
    logger.bind(request_id=get_request_id()).info(
        f"获取上传URL: {current_user.username}, key={upload_info['object_key']}")
    return {
        "msg": "获取上传地址成功",
        "upload_url": upload_info["upload_url"],
        "object_key": upload_info["object_key"],
        "expires_in": upload_info["expires_in"]
    }


@app.post("/upload/callback")
def upload_callback(data: UploadCallback,
                    current_user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    update_user_avatar(db, current_user.id, data.object_key)
    avatar_url = get_file_url(data.object_key)
    logger.bind(request_id=get_request_id()).info(f"头像更新成功: {current_user.username}")
    return {"msg": "头像更新成功", "avatar_url": avatar_url}


# ==================== 用户信息 ====================
@app.get("/user/me")
def read_current_user(current_user=Depends(get_current_user)):
    return {
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat()
    }


@app.get("/user/profile")
def get_user_profile(current_user=Depends(get_current_user)):
    avatar_url = get_file_url(current_user.avatar_key) if current_user.avatar_key else None
    return {
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat(),
        "avatar_url": avatar_url
    }


@app.post("/blindbox/open")
def blindbox_open(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
       用户点击开箱：
       1. 先在数据库创建订单（status=pending）
       2. 把订单ID发给 Celery 异步执行
       """
    # 创建订单
    order = create_order(db, current_user.id)

    # 发送异步任务
    task = open_blind_box.delay(order_id=order.id, user_id=current_user.id)

    logger.bind(request_id=get_request_id()).info(f"开箱任务已发送: order_id={order.id}, task_id={task.id}")

    return {
        "msg": "开箱任务已提交，正在处理中....",
        "order_id": order.id,
        "task_id": task.id
    }


@app.get("/blindbox/result/{task_id}")
def blindbox_result(task_id: str):
    task_result = celery_app.AsyncResult(task_id)

    if task_result.state == "PENDING":
        return {"status": "处理中...", "task_id": task_id}
    elif task_result.state == "SUCCESS":
        return {"status": "完成", "result": task_result.result}
    elif task_result.state == "FAILURE":
        return {"status": "失败", "error": str(task_result.info)}
    else:
        return {"status": task_result.state, "task_id": task_id}


# 健康检查
@app.get("/health")
def health_chech():
    return {"status": "ok"}
