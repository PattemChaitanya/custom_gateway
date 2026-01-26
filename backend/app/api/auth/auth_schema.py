from pydantic import BaseModel, EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

class SendCode(BaseModel):
    # used for sending OTPs or email verification codes
    email: EmailStr | None = None
    mobile: str | None = None

class TokenRefresh(BaseModel):
    refresh_token: str

class EmailVerification(BaseModel):
    email: EmailStr
    code: str

class OTPVerification(BaseModel):
    email: EmailStr | None = None
    otp: str

