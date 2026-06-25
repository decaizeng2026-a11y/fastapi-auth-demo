import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import fake_db, User
from logger import get_request_id,logger


"""配置"""
# 密匙，实际项目应从环境变量读取
SECRET_KEY = "your_secret_key_keep_it_safe"
# 加密算法
ALGORITHM = "HS256"
# access token有效期
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 告诉fastapi从那个接口获取token，tokenurl指的是登录接口的路径
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

"""密码加密和验证"""


#    对明文密码进行 bcrypt 加密,返回加密后的字符串，可直接存入数据库
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()  # 生成随机盐值
    hashed = bcrypt.hashpw(  # 用盐值对密码进行哈希
        password.encode('utf-8'),  # 密码必须先转成字节串
        salt
    )
    return hashed.decode('utf-8')  # 哈希结果转回字符串存储


"""对密码进行验证"""


# 验证明文密码是否和数据库中的秘文匹配
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


"""JWT签发与解码"""


# 签发 JWT Access Token,data 里通常包含用户标识，如 {"sub": "zhangsan"}
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_jwt


"""鉴权依赖"""
# 从请求中提取并校验 Token，返回当前用户
def get_create_user(token:str = Depends(oauth2_scheme)):
    print("BEBUG request_id",get_request_id())
    # 1.解码token
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        username:str = payload.get("sub")
        if username is None:
            logger.bind(get_request_id=get_request_id()).warning("Token中缺少用户标识")
            raise HTTPException(status_code=401)
    except jwt.PyJWTError:
        # 解码失败：过期，伪造，密匙不对
        logger.bind(request_id=get_request_id()).warning("Token解码失败")
        raise HTTPException(status_code=401)

    # 2.查数据库确认用户存在
    user = fake_db.get(username)
    if user is None:
        logger.bind(request_id=get_request_id()).warning(f"用户不存在：{username}")
        raise HTTPException(status_code=401)

    logger.bind(request_id=get_request_id()).info(f"用户鉴权成功：{username}")
    return user