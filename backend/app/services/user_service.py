"""Admin user-management service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _validate_station(role: UserRole, station) -> None:
        if role == UserRole.ADMIN:
            if station is not None:
                raise ValidationError(
                    "ADMIN_STATION_NOT_ALLOWED",
                    "An administrator account cannot be tied to a station.",
                )
        elif station is None:
            raise ValidationError(
                "STATION_REQUIRED",
                "A station is required for every non-admin role.",
            )

    async def create(self, payload: UserCreate) -> User:
        self._validate_station(payload.role, payload.assigned_station)
        existing = await self.session.scalar(
            select(User.id).where(func.lower(User.username) == payload.username.lower())
        )
        if existing is not None:
            raise ConflictError("USERNAME_TAKEN", "That username is already in use.")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            assigned_station=payload.assigned_station,
            default_shift_start=payload.default_shift_start,
            is_active=True,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("USERNAME_TAKEN", "That username is already in use.") from exc
        await self.session.refresh(user)
        return user

    async def update(self, user_id: int, payload: UserUpdate, actor_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise NotFoundError("User")

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return user

        new_role = changes.get("role", user.role)
        if "assigned_station" in changes:
            new_station = changes["assigned_station"]
            self._validate_station(new_role, new_station)
            user.assigned_station = new_station
        elif "role" in changes:
            self._validate_station(new_role, user.assigned_station)
        user.role = new_role

        if "full_name" in changes:
            user.full_name = " ".join(changes["full_name"].split())
        if "default_shift_start" in changes:
            user.default_shift_start = changes["default_shift_start"]
        if "is_active" in changes:
            if user.id == actor_id and not changes["is_active"]:
                raise ValidationError(
                    "CANNOT_DISABLE_SELF",
                    "You cannot disable your own administrator account.",
                )
            user.is_active = changes["is_active"]
        if changes.get("password"):
            user.password_hash = hash_password(changes["password"])

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("USER_UPDATE_CONFLICT", "The account could not be updated.") from exc
        await self.session.refresh(user)
        return user

    async def get(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise NotFoundError("User")
        return user

    async def list(
        self,
        *,
        search: str | None,
        role: UserRole | None,
        station,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        filters = []
        if search:
            needle = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(User.username).like(needle),
                    func.lower(User.full_name).like(needle),
                )
            )
        if role is not None:
            filters.append(User.role == role)
        if station is not None:
            filters.append(User.assigned_station == station)
        if active_only:
            filters.append(User.is_active.is_(True))

        total = await self.session.scalar(
            select(func.count(User.id)).where(*filters)
        )
        users = (
            await self.session.scalars(
                select(User)
                .where(*filters)
                .order_by(User.full_name.asc(), User.id.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return list(users), int(total or 0)
