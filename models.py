from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    players = relationship("Player", back_populates="game")
    votings = relationship("Voting", back_populates="game")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    telegram_id = Column(String, nullable=True)
    name = Column(String)
    role = Column(String, nullable=True)
    alive = Column(Boolean, default=True)

    game = relationship("Game", back_populates="players")


class Voting(Base):
    __tablename__ = "votings"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", back_populates="votings")
    votes = relationship("Vote", back_populates="voting")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    voting_id = Column(Integer, ForeignKey("votings.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    target_player_id = Column(Integer, ForeignKey("players.id"))

    voting = relationship("Voting", back_populates="votes")
