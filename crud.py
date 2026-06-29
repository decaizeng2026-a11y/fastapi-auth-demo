from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from database import User, ExamRecord, BlindBoxItem, OpenRecord,Order


# -------------用户--------------
# 创建用户
def create_user(db: Session, username: str, hashed_password: str, phone: str = None):
    db_user = User(username=username, hashed_password=hashed_password, phone=phone)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# 通过用户名查询用户信息
def get_user_by_username(db: Session, username: str):
    stmt = select(User).where(User.username == username)
    return db.execute(stmt).scalar_one_or_none()


# 根据手机号查询用户信息
def get_user_by_phone(db: Session, phone: str):
    stmt = select(User).where(User.phone == phone)
    return db.execute(stmt).scalar_one_or_none()


# 更新用户头像
def update_user_avatar(db: Session, user_id: int, avatar_key: str):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user:
        user.avatar_key = avatar_key
        db.commit()
        db.refresh(user)
    return user



# -------------考试记录--------------
def create_exam_record(db:Session,user_id:int,exam_id:int,score:float):
    record = ExamRecord(user_id=user_id,exam_id=exam_id,score=score)
    db.add()
    db.commit()
    db.refresh()
    return record


def get_user_exam_records(db:Session,user_id:int,skip:int = 0,limint:int = 10):
    stmt = (
        select(ExamRecord)
        .where(ExamRecord.user_id == user_id)
        .order_by(ExamRecord.exam_time.desc())
        .offset(skip)
        .limit(limint)
    )
    return db.execute(stmt).scalars().all()


# -----------盲盒商品-------------
def get_all_items(db:Session):
    return db.execute(select(BlindBoxItem)).scalars().all()


def decrease_stock(db:Session,item_id:int):
    stmt = (
        update(BlindBoxItem)
        .where(BlindBoxItem.id == item_id, BlindBoxItem.stock > 0)
        .values(stock=BlindBoxItem.stock - 1)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0


# -------------------开箱记录---------------
def create_open_record(db:Session,user_id:int,item_id:int):
    record = OpenRecord(user_id=user_id,item_id=item_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ==================== 订单相关 ====================
def create_order(db: Session, user_id: int) -> Order:
    """创建一条待处理的订单"""
    order = Order(user_id=user_id, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
    """根据订单ID查订单"""
    stmt = select(Order).where(Order.id == order_id)
    return db.execute(stmt).scalar_one_or_none()


def update_order_status(db: Session, order_id: int, status: str) -> Optional[Order]:
    """更新订单状态"""
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order:
        order.status = status
        db.commit()
        db.refresh(order)
    return order