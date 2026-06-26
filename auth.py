import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import get_db
from crud import get_user_by_username, get_user_by_phone
from logger import get_request_id, logger
from sqlalchemy.orm import Session

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
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """从JWT中解析用户，然后查数据验证"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"www_Authenticate": "Bearer"}
    )
    # 1.解码token
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        username_or_phone: str = payload.get("sub")
        if username_or_phone is None:
            logger.bind(get_request_id=get_request_id()).warning("Token中缺少用户标识")
            raise credentials_exception
    except jwt.PyJWTError:
        # 解码失败：过期，伪造，密匙不对
        logger.bind(request_id=get_request_id()).warning("Token解码失败")
        raise credentials_exception

    # 2.尝试用用户名查，不行就用手机号查
    user = get_user_by_username(db, username_or_phone)
    if not user:
        logger.bind(request_id=get_request_id()).warning(f"用户不存在：{username_or_phone}")
        raise credentials_exception

    logger.bind(request_id=get_request_id()).info(f"用户鉴权成功：{user.username}")
    return user
