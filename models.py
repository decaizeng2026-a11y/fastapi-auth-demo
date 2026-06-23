from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserProfileResponse(BaseModel):
    username: str
    created_at: str


class SMSSend(BaseModel):
    phone: str


class SMSLogin(BaseModel):
    phone: str
    code: str
