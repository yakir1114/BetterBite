"""SQLAlchemy models — the database schema from docs/03_Database_Schema.md.

Conventions (docs/03 §1):
- UUID primary keys defaulting to ``gen_random_uuid()`` (requires pgcrypto).
- ``created_at`` everywhere; ``updated_at`` on mutable tables. TIMESTAMPTZ, UTC.
- All nutrition values are metric (g, kcal, ml, kg, cm).
- Every owned row carries ``user_id`` for row-level scoping.

The Alembic migration adds the ``pgcrypto`` and ``pg_trgm`` extensions that the
UUID default and the fuzzy food-name index rely on.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# --------------------------------------------------------------------------- #
# Enum types (docs/03 §3)
# --------------------------------------------------------------------------- #
class SexEnum(enum.StrEnum):
    male = "male"
    female = "female"
    other = "other"


class ActivityLevelEnum(enum.StrEnum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class GoalTypeEnum(enum.StrEnum):
    lose_weight = "lose_weight"
    gain_muscle = "gain_muscle"
    maintain = "maintain"


class MealTypeEnum(enum.StrEnum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealSourceEnum(enum.StrEnum):
    photo = "photo"
    manual = "manual"
    barcode = "barcode"
    recipe = "recipe"


class ItemSourceEnum(enum.StrEnum):
    ai = "ai"
    catalog = "catalog"
    manual = "manual"


class InsightScopeEnum(enum.StrEnum):
    meal = "meal"
    daily = "daily"
    weekly = "weekly"


class ChatRoleEnum(enum.StrEnum):
    user = "user"
    assistant = "assistant"


class NotifTypeEnum(enum.StrEnum):
    meal_reminder = "meal_reminder"
    water_reminder = "water_reminder"
    coach = "coach"
    achievement = "achievement"
    custom = "custom"


class WeightSourceEnum(enum.StrEnum):
    manual = "manual"
    google_fit = "google_fit"
    samsung_health = "samsung_health"
    healthkit = "healthkit"


def _pg_enum(py_enum: type[enum.Enum], name: str) -> Enum:
    """Build a Postgres ENUM that stores the lowercase *values* (not member names)."""
    return Enum(
        py_enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        create_type=True,
    )


# --------------------------------------------------------------------------- #
# Column helpers
# --------------------------------------------------------------------------- #
def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


def _updated_at() -> Mapped[datetime]:
    return mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
    )


def _user_fk(*, index: bool = True) -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=index,
    )


# --------------------------------------------------------------------------- #
# 4.1 users
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    firebase_uid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    sex: Mapped[SexEnum | None] = mapped_column(_pg_enum(SexEnum, "sex_enum"))
    birth_date: Mapped[date | None] = mapped_column(Date)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    activity_level: Mapped[ActivityLevelEnum | None] = mapped_column(
        _pg_enum(ActivityLevelEnum, "activity_level_enum")
    )
    locale: Mapped[str] = mapped_column(Text, server_default=text("'he'"), nullable=False)
    units_metric: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    dark_mode: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    xp: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    streak_days: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    onboarded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


# --------------------------------------------------------------------------- #
# 4.2 goals
# --------------------------------------------------------------------------- #
class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        # docs/03 §6: only one active goal per user.
        Index(
            "uq_goals_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk()
    goal_type: Mapped[GoalTypeEnum] = mapped_column(
        _pg_enum(GoalTypeEnum, "goal_type_enum"), nullable=False
    )
    start_weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1))
    target_weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1))
    bmr_kcal: Mapped[float | None] = mapped_column(Numeric(7, 1))
    tdee_kcal: Mapped[float | None] = mapped_column(Numeric(7, 1))
    daily_kcal_target: Mapped[float | None] = mapped_column(Numeric(7, 1))
    protein_g_target: Mapped[float | None] = mapped_column(Numeric(6, 1))
    carbs_g_target: Mapped[float | None] = mapped_column(Numeric(6, 1))
    fat_g_target: Mapped[float | None] = mapped_column(Numeric(6, 1))
    water_ml_target: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


# --------------------------------------------------------------------------- #
# 4.3 foods
# --------------------------------------------------------------------------- #
class Food(Base):
    __tablename__ = "foods"
    __table_args__ = (
        Index("idx_foods_barcode", "barcode"),
        Index(
            "idx_foods_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_he: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    barcode: Mapped[str | None] = mapped_column(Text)
    is_liquid: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    kcal_per_100: Mapped[float | None] = mapped_column(Numeric(7, 2))
    protein_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    carbs_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fat_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fiber_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sugar_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sodium_mg_per_100: Mapped[float | None] = mapped_column(Numeric(7, 2))
    is_processed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    saturated_fat_per_100: Mapped[float | None] = mapped_column(Numeric(6, 2))
    source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.4 meals
# --------------------------------------------------------------------------- #
class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (
        Index("idx_meals_user_date", "user_id", text("logged_date DESC")),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)  # covered by idx_meals_user_date
    meal_type: Mapped[MealTypeEnum] = mapped_column(
        _pg_enum(MealTypeEnum, "meal_type_enum"), nullable=False
    )
    eaten_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[MealSourceEnum] = mapped_column(
        _pg_enum(MealSourceEnum, "meal_source_enum"), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    total_kcal: Mapped[float | None] = mapped_column(Numeric(8, 2))
    total_protein_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_carbs_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_fat_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_fiber_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_sugar_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_sodium_mg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    health_score: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    items: Mapped[list[MealItem]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# --------------------------------------------------------------------------- #
# 4.5 meal_items
# --------------------------------------------------------------------------- #
class MealItem(Base):
    __tablename__ = "meal_items"
    __table_args__ = (Index("idx_meal_items_meal", "meal_id"),)

    id: Mapped[uuid.UUID] = _pk()
    meal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_g: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    source: Mapped[ItemSourceEnum] = mapped_column(
        _pg_enum(ItemSourceEnum, "item_source_enum"), nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    kcal: Mapped[float | None] = mapped_column(Numeric(7, 2))
    protein_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fat_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fiber_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sugar_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sodium_mg: Mapped[float | None] = mapped_column(Numeric(7, 2))
    edited_by_user: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()

    meal: Mapped[Meal] = relationship(back_populates="items")


# --------------------------------------------------------------------------- #
# 4.6 daily_summaries
# --------------------------------------------------------------------------- #
class DailySummary(Base):
    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_summaries_user_date"),
        Index("idx_daily_user_date", "user_id", text("date DESC")),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    kcal_total: Mapped[float | None] = mapped_column(Numeric(8, 2))
    kcal_target: Mapped[float | None] = mapped_column(Numeric(8, 2))
    protein_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    fat_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    fiber_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    sugar_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    sodium_mg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    water_ml: Mapped[int | None] = mapped_column(Integer)
    meals_count: Mapped[int | None] = mapped_column(SmallInteger)
    health_score: Mapped[int | None] = mapped_column(SmallInteger)
    goal_met: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


# --------------------------------------------------------------------------- #
# 4.7 weight_history
# --------------------------------------------------------------------------- #
class WeightHistory(Base):
    __tablename__ = "weight_history"
    __table_args__ = (
        Index("idx_weight_user_time", "user_id", text("measured_at DESC")),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    bmi: Mapped[float | None] = mapped_column(Numeric(4, 1))
    measured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    source: Mapped[WeightSourceEnum] = mapped_column(
        _pg_enum(WeightSourceEnum, "weight_source_enum"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.8 water_logs
# --------------------------------------------------------------------------- #
class WaterLog(Base):
    __tablename__ = "water_logs"
    __table_args__ = (Index("idx_water_user_date", "user_id", "logged_date"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


# --------------------------------------------------------------------------- #
# 4.9 achievements / user_achievements
# --------------------------------------------------------------------------- #
class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[uuid.UUID] = _pk()
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    title_he: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    xp_reward: Mapped[int | None] = mapped_column(Integer)
    criteria: Mapped[dict | None] = mapped_column(JSONB)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "achievement_id", name="uq_user_achievements_user_achievement"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    earned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


# --------------------------------------------------------------------------- #
# 4.10 tasks / user_tasks
# --------------------------------------------------------------------------- #
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = _pk()
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    title_he: Mapped[str | None] = mapped_column(Text)
    xp_reward: Mapped[int | None] = mapped_column(Integer)
    criteria: Mapped[dict | None] = mapped_column(JSONB)
    cadence: Mapped[str] = mapped_column(
        Text, server_default=text("'daily'"), nullable=False
    )


class UserTask(Base):
    __tablename__ = "user_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", "date", name="uq_user_tasks_user_task_date"),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


# --------------------------------------------------------------------------- #
# 4.11 coach_insights
# --------------------------------------------------------------------------- #
class CoachInsight(Base):
    __tablename__ = "coach_insights"
    __table_args__ = (
        Index("idx_insights_user_time", "user_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    scope: Mapped[InsightScopeEnum] = mapped_column(
        _pg_enum(InsightScopeEnum, "insight_scope_enum"), nullable=False
    )
    meal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meals.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    context: Mapped[dict | None] = mapped_column(JSONB)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.12 chat_messages
# --------------------------------------------------------------------------- #
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_chat_user_time", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    role: Mapped[ChatRoleEnum] = mapped_column(
        _pg_enum(ChatRoleEnum, "chat_role_enum"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.13 recipes / recipe_ingredients
# --------------------------------------------------------------------------- #
class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )  # null = global/seed recipe
    title: Mapped[str | None] = mapped_column(Text)
    title_he: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    prep_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    servings: Mapped[int | None] = mapped_column(SmallInteger)
    kcal_per_serving: Mapped[float | None] = mapped_column(Numeric(7, 2))
    protein_g_per_serving: Mapped[float | None] = mapped_column(Numeric(6, 2))
    carbs_g_per_serving: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fat_g_per_serving: Mapped[float | None] = mapped_column(Numeric(6, 2))
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = _created_at()

    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[uuid.UUID] = _pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    display_amount: Mapped[str | None] = mapped_column(Text)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


# --------------------------------------------------------------------------- #
# 4.14 shopping_list_items
# --------------------------------------------------------------------------- #
class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[str | None] = mapped_column(Text)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"), index=True
    )
    checked: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.15 notifications
# --------------------------------------------------------------------------- #
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("idx_notif_user_sched", "user_id", "scheduled_for"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk(index=False)
    type: Mapped[NotifTypeEnum] = mapped_column(
        _pg_enum(NotifTypeEnum, "notif_type_enum"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created_at()


# --------------------------------------------------------------------------- #
# 4.16 devices
# --------------------------------------------------------------------------- #
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _user_fk()
    fcm_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    platform: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = _created_at()
