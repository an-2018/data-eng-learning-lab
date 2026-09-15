from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL

def now():
    return datetime.now(timezone.utc)

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    role = Column(String, default='learner')

class Workspace(Base):
    __tablename__ = 'workspaces'
    __table_args__ = (UniqueConstraint('user_id', 'exercise_id'),)
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    exercise_id = Column(String, nullable=False)
    files = Column(JSON, default=dict)
    revision = Column(Integer, default=1)
    assisted = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=now)

class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (UniqueConstraint('user_id', 'idempotency_key'),)
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    exercise_id = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    mode = Column(String, default='practice')
    files = Column(JSON, nullable=False)
    answers = Column(JSON, default=dict)
    version = Column(String, nullable=False)
    runtime_version = Column(String, nullable=False)
    dataset_version = Column(String, default='1')
    grader_version = Column(String, default='1')
    content_hash = Column(String, nullable=False)
    status = Column(String, default='queued', index=True)
    feedback = Column(JSON, default=dict)
    assisted = Column(Boolean, default=False)
    cancel_requested = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    lease_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

class Progress(Base):
    __tablename__ = 'progress'
    __table_args__ = (UniqueConstraint('user_id', 'exercise_id'),)
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    exercise_id = Column(String)
    state = Column(String, default='learning')
    review_step = Column(Integer, default=0)
    review_at = Column(DateTime(timezone=True))
    last_job_id = Column(String)
    passed_variants = Column(JSON, default=list)

class Reading(Base):
    __tablename__ = 'readings'
    __table_args__ = (UniqueConstraint('user_id', 'lesson_id'),)
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    lesson_id = Column(String)
    read_at = Column(DateTime(timezone=True), default=now)

class TutorMessage(Base):
    __tablename__ = 'tutor_messages'
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    exercise_id = Column(String)
    question = Column(Text)
    answer = Column(Text)
    reserved_cents = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), default=now)

class Milestone(Base):
    __tablename__ = 'milestones'
    __table_args__ = (UniqueConstraint('user_id', 'project_id', 'milestone_id'),)
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    project_id = Column(String)
    milestone_id = Column(String)
    notes = Column(Text, default='')
    completed = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    with Session() as session:
        yield session
