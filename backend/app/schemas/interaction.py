from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

QuestionStatus = Literal["open", "answered", "closed"]


def _strip_body(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("النص لا يمكن أن يكون فارغاً")
    return v


Body = Annotated[str, Field(max_length=5000), AfterValidator(_strip_body)]


class CommentIn(BaseModel):
    body: Body
    session_id: int | None = None


class QuestionIn(BaseModel):
    body: Body
    session_id: int | None = None


class ReplyIn(BaseModel):
    body: Body


class QuestionStatusIn(BaseModel):
    status: QuestionStatus


class ReplyOut(BaseModel):
    id: int
    author_id: int | None
    author_name: str | None
    author_role: str | None
    body: str
    created_at: datetime


class QuestionOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    session_id: int | None
    session_date: date | None
    body: str
    status: QuestionStatus
    created_at: datetime
    updated_at: datetime
    replies: list[ReplyOut]
