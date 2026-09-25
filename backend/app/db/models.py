"""Modelos ORM (SQLAlchemy 2.x): `users`, `lugar_turistico` y `visitas_historicas`."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    # Hash bcrypt. Nunca se expone en respuestas ni se loggea.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LugarTuristico(Base):
    """Lugar turistico. Los demas modulos lo buscan por `codigo`, nunca por `id`."""

    __tablename__ = "lugar_turistico"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    sitio: Mapped[str] = mapped_column(String(120), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(120), nullable=False)
    # Valores informativos (mock): no limitan los datos historicos.
    horario: Mapped[str] = mapped_column(String(60), nullable=False)
    aforo_maximo: Mapped[int] = mapped_column(Integer, nullable=False)


class VisitaHistorica(Base):
    """Visitas diarias historicas de un lugar turistico."""

    __tablename__ = "visitas_historicas"
    __table_args__ = (
        UniqueConstraint("lugar_id", "fecha"),
        CheckConstraint("visitantes_totales >= 0"),
        Index(
            "ix_visitas_similitud",
            "lugar_id",
            "dia_semana",
            "condicion_clima",
            "es_feriado",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lugar_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lugar_turistico.id"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    dia_semana: Mapped[str] = mapped_column(String(10), nullable=False)
    condicion_clima: Mapped[str] = mapped_column(String(25), nullable=False)
    temperatura_max: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    es_feriado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    temporada: Mapped[str] = mapped_column(String(12), nullable=False)
    visitantes_totales: Mapped[int] = mapped_column(Integer, nullable=False)
