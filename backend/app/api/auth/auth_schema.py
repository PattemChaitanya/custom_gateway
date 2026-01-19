from pydantic import BaseModel, EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

class TokenRefresh(BaseModel):
    refresh_token: str

class EmailVerification(BaseModel):
    email: EmailStr
    code: str

class OTPVerification(BaseModel):
    otp: str

