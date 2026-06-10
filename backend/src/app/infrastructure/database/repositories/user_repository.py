from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models import User
from app.services.auth_service import AuthService


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def get_or_create_by_email(self, email: str) -> User:
        user = self.get_by_email(email)
        if user:
            return user
        random_password = str(uuid.uuid4())
        hashed_pwd = AuthService.hash_password(random_password)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hashed_pwd,
        )
        self.session.add(user)
        self.session.flush()
        return user

