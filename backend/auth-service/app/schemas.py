from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    name: str
    phone: str | None = None
    email: str
    balance: float

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    user: UserOut