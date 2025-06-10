from pydantic import BaseModel


class DrawUserResponse(BaseModel):
    id: int
    telegram_id: int
    first_name: str
    last_name: str
    phone: str

    class Config:
        orm_mode = True
