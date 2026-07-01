from datetime import datetime
from sqlalchemy import create_engine,String,Integer,Float,DateTime,TEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, sessionmaker, Session, mapped_column
from datetime import datetime
from typing import Optional
import os


# 数据库链接
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/exam_system"
# 数据库链接(docker-compose版本)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123456@localhost:3306/exam_system"
)



engine = create_engine(SQLALCHEMY_DATABASE_URL,echo=False)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

# 基类模型
class Base(DeclarativeBase):
    pass

# 数据表模型
class User(Base):
    __tablename__ = "users"

    id:Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    username:Mapped[str] = mapped_column(String(50),unique=True,index=True,nullable=False)
    hashed_password:Mapped[str] = mapped_column(String(255),nullable=False)
    phone:Mapped[str] = mapped_column(String(20),unique=True,index=True,nullable=True)
    avatar_key:Mapped[str] = mapped_column(String(255),nullable=True)
    created_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow)


class ExamRecord(Base):
    __tablename__ = "exam_records"

    id:Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    user_id:Mapped[int] = mapped_column(Integer,nullable=False,index=True)
    exam_id:Mapped[int] = mapped_column(Integer,nullable=False)
    SCORE:Mapped[Optional[float]] = mapped_column(Float,nullable=True)
    exam_time:Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow)



class BlindBoxItem(Base):
    __tablename__ = "blind_box_items"

    id:Mapped[int] = mapped_column(Integer,primary_key=True,nullable=False)
    name:Mapped[str] = mapped_column(String(100),nullable=False)
    stock:Mapped[int] = mapped_column(Integer,default=0)
    rarity:Mapped[str] = mapped_column(String(20),default="普通")
    image_url:Mapped[str] = mapped_column(TEXT,nullable=True)



class OpenRecord(Base):
    __tablename__ = "open_records"

    id:Mapped[int] = mapped_column(Integer,primary_key=True)
    user_id:Mapped[int] = mapped_column(Integer,nullable=False,index=True)
    item_id:Mapped[int] = mapped_column(Integer,nullable=False)
    open_time:Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/processing/done/failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Order(id={self.id}, status={self.status})>"



# 水文数据表
class HydrologyRecord(Base):
    __tablename__ = "hydrology_records"

    id:Mapped[int] = mapped_column(Integer,primary_key=True)
    water_level:Mapped[float] = mapped_column(Float,nullable=False,comment="水位")
    flow_speed:Mapped[float] = mapped_column(Float,nullable=False,comment="流速")
    recorded_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow,comment="采集时间")

    def __repr__(self):
        return f"<HydrologyRecord(id={self.id}, water_level={self.water_level})>"





# =========创建所有表========
Base.metadata.create_all(bind=engine)

# ===========FastAPI依赖注入============
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()