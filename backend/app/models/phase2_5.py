"""Phase 2-5 models: Pomodoro, Questions, Flashcards, Exams, Diary, etc."""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# ---- Phase 2: Pomodoro ----
class PomodoroRecord(Base):
    __tablename__ = "pomodoro_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[str | None] = mapped_column(String(36))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    planned_minutes: Mapped[int] = mapped_column(Integer, default=25)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed | abandoned
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Phase 3: Daily Questions ----
class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject: Mapped[str] = mapped_column(String(20), nullable=False)  # 408|math|politics|english
    sub_subject: Mapped[str | None] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(20))  # single_choice|multi_choice|fill_blank
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[str | None] = mapped_column(Text)  # JSON
    answer: Mapped[str] = mapped_column(String(200), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(200))
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserAnswer(Base):
    __tablename__ = "user_answers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), nullable=False)
    user_choice: Mapped[str] = mapped_column(String(200))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Error Notebook ----
class ErrorNote(Base):
    __tablename__ = "error_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="daily_question")  # daily_question|mock_exam|flashcard
    wrong_answer: Mapped[str] = mapped_column(String(200))
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Flashcards ----
class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    card_count: Mapped[int] = mapped_column(Integer, default=0)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True)
    creator_id: Mapped[str | None] = mapped_column(String(36))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcard_decks.id"), nullable=False, index=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserCardProgress(Base):
    __tablename__ = "user_card_progress"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcards.id"), nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_rating: Mapped[int | None] = mapped_column(Integer)  # 1-4
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Phase 4: Diary ----
class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text)
    mood: Mapped[str | None] = mapped_column(String(20))  # happy|anxious|tired|motivated|neutral
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    pomodoro_count: Mapped[int] = mapped_column(Integer, default=0)
    pomodoro_minutes: Mapped[int] = mapped_column(Integer, default=0)
    daily_question_correct: Mapped[bool | None] = mapped_column(Boolean)
    flashcards_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    ai_reply: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ---- Fortune ----
class FortuneRecord(Base):
    __tablename__ = "fortune_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    level: Mapped[str] = mapped_column(String(10))  # 大吉|吉|小吉|末吉|凶
    color: Mapped[str] = mapped_column(String(10))
    number: Mapped[int] = mapped_column(Integer, default=0)
    good: Mapped[str] = mapped_column(String(100))
    bad: Mapped[str] = mapped_column(String(100))
    quote: Mapped[str] = mapped_column(String(200))
    score: Mapped[int] = mapped_column(Integer, default=50)
    shared_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Phase 5: Mock Exam ----
class MockExam(Base):
    __tablename__ = "mock_exams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    total_score: Mapped[int] = mapped_column(Integer, default=150)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=180)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    sections: Mapped[str | None] = mapped_column(Text)  # JSON
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserExam(Base):
    __tablename__ = "user_exams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    exam_id: Mapped[str] = mapped_column(String(36), ForeignKey("mock_exams.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress|submitted|abandoned
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    max_score: Mapped[int] = mapped_column(Integer, default=150)
    answers: Mapped[str | None] = mapped_column(Text)  # JSON
    marked_questions: Mapped[str | None] = mapped_column(Text)  # JSON
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Transfer (调剂) ----
class TransferInfo(Base):
    __tablename__ = "transfer_infos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_name: Mapped[str] = mapped_column(String(100), nullable=False)
    school_id: Mapped[str | None] = mapped_column(String(36))
    major: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(10), default="学硕")
    requirement: Mapped[str | None] = mapped_column(Text)
    min_score: Mapped[int | None] = mapped_column(Integer)
    contact: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))
    publish_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserTransferAlert(Base):
    __tablename__ = "user_transfer_alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    keywords: Mapped[str] = mapped_column(String(200))
    provinces: Mapped[str | None] = mapped_column(String(200))
    min_level: Mapped[str | None] = mapped_column(String(10))
    max_score: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Study Plan ----
class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(10))  # weekly|daily
    week_start: Mapped[date | None] = mapped_column(Date)
    date: Mapped[date | None] = mapped_column(Date)
    content: Mapped[str | None] = mapped_column(Text)  # JSON
    generated_by: Mapped[str] = mapped_column(String(10), default="ai")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# ---- Interview ----
class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20))  # english|professional|comprehensive|full
    target_school: Mapped[str] = mapped_column(String(100))
    target_major: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    total_score: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class InterviewQA(Base):
    __tablename__ = "interview_qa"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[str | None] = mapped_column(Text)
    score_content: Mapped[int | None] = mapped_column(Integer)
    score_expression: Mapped[int | None] = mapped_column(Integer)
    score_confidence: Mapped[int | None] = mapped_column(Integer)
    feedback: Mapped[str | None] = mapped_column(Text)
    suggested_answer: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

# ---- Achievement (Phase 4) ----
class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20))
    icon: Mapped[str] = mapped_column(String(10))
    condition_type: Mapped[str] = mapped_column(String(30))
    condition_value: Mapped[int] = mapped_column(Integer, default=1)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    achievement_id: Mapped[str] = mapped_column(String(36), ForeignKey("achievements.id"), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
