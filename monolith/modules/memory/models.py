import uuid
from datetime import datetime

from sqlalchemy import UUID, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from monolith.shared.db.base import Base

# Ledger: registro NOSSO, por fora do motor, de cada turno entregue à memória e
# de cada escrita que o motor reportou. É a ground truth da proveniência —
# memória → turno → sources do RAG → documento — contra a qual se mede o que o
# motor consegue responder sozinho.


class LedgerTurn(Base):
    __tablename__ = "memory_ledger_turns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    engine: Mapped[str] = mapped_column(String(50))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    # SET NULL e não CASCADE: apagar a collection não pode apagar a evidência de
    # que um documento dela contaminou a memória.
    collection_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
    )
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)
    # As sources do RAG vistas no turno (mesmo formato do evento SSE 'sources').
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    # Ids (do motor) das memórias injetadas no prompt deste turno.
    recalled_memory_ids: Mapped[list] = mapped_column(JSONB, default=list)
    # Falha do motor ao gravar. O turno fica registrado mesmo assim.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    writes: Mapped[list["LedgerWrite"]] = relationship(
        "LedgerWrite", back_populates="turn", cascade="all, delete-orphan"
    )


class LedgerWrite(Base):
    __tablename__ = "memory_ledger_writes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    turn_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("memory_ledger_turns.id", ondelete="CASCADE")
    )
    # Id da memória NO MOTOR — é a chave que liga o que o motor devolve ao ledger.
    memory_id: Mapped[str] = mapped_column(String(255), index=True)
    event: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    turn: Mapped["LedgerTurn"] = relationship("LedgerTurn", back_populates="writes")
