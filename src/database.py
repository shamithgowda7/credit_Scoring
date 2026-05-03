"""
Database Layer — SQLite Persistence for LLM Assessment Sessions
================================================================
Manages:
  - assessment_sessions: top-level session tracking
  - conversation_turns: individual Q&A turn records with timestamps

Uses built-in sqlite3 for zero-dependency operation.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_scoring.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS assessment_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            bank_context TEXT NOT NULL,
            qa_history TEXT DEFAULT '[]',
            status TEXT DEFAULT 'IN_PROGRESS',
            extracted_features TEXT,
            final_score INTEGER,
            decision TEXT,
            risk_tier TEXT,
            total_turns INTEGER DEFAULT 0,
            interview_duration_sec REAL,
            extraction_confidence TEXT,
            graph_profile_id INTEGER,
            is_mock_mode INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_number INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT,
            dimension TEXT,
            user_answer TEXT,
            response_latency_sec REAL,
            llm_raw_response TEXT,
            is_catch_trial INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES assessment_sessions(session_id)
        )
    ''')

    conn.commit()
    conn.close()


# ── Session CRUD ──────────────────────────────────────────────────────────────

def create_session(session_id: str, name: str, bank_context: str, is_mock: bool = False):
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO assessment_sessions 
           (session_id, name, bank_context, is_mock_mode) 
           VALUES (?, ?, ?, ?)''',
        (session_id, name, bank_context, 1 if is_mock else 0)
    )
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[dict]:
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM assessment_sessions WHERE session_id = ?',
        (session_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_session_history(session_id: str, qa_history: list):
    conn = get_db_connection()
    conn.execute(
        '''UPDATE assessment_sessions 
           SET qa_history = ?, total_turns = ?, updated_at = CURRENT_TIMESTAMP 
           WHERE session_id = ?''',
        (json.dumps(qa_history), len(qa_history), session_id)
    )
    conn.commit()
    conn.close()


def finalize_session(session_id: str, features: dict, score: int, 
                     decision: str, risk_tier: str = None,
                     confidence: str = None, duration_sec: float = None):
    conn = get_db_connection()
    conn.execute(
        '''UPDATE assessment_sessions 
           SET status = 'COMPLETED', 
               extracted_features = ?, 
               final_score = ?, 
               decision = ?,
               risk_tier = ?,
               extraction_confidence = ?,
               interview_duration_sec = ?,
               updated_at = CURRENT_TIMESTAMP 
           WHERE session_id = ?''',
        (json.dumps(features), score, decision, risk_tier, 
         confidence, duration_sec, session_id)
    )
    conn.commit()
    conn.close()


# ── Conversation Turns ────────────────────────────────────────────────────────

def add_conversation_turn(session_id: str, turn_number: int,
                          question_text: str, options: list = None,
                          dimension: str = None, user_answer: str = None,
                          response_latency_sec: float = None,
                          llm_raw_response: str = None,
                          is_catch_trial: bool = False):
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO conversation_turns 
           (session_id, turn_number, question_text, options, dimension,
            user_answer, response_latency_sec, llm_raw_response, is_catch_trial)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (session_id, turn_number, question_text,
         json.dumps(options) if options else None,
         dimension, user_answer, response_latency_sec,
         llm_raw_response, 1 if is_catch_trial else 0)
    )
    conn.commit()
    conn.close()


def get_session_turns(session_id: str) -> List[dict]:
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT * FROM conversation_turns 
           WHERE session_id = ? 
           ORDER BY turn_number ASC''',
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Aggregation Queries ──────────────────────────────────────────────────────

def get_all_completed_sessions() -> List[dict]:
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT * FROM assessment_sessions 
           WHERE status = 'COMPLETED' 
           ORDER BY created_at DESC'''
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sessions_summary() -> dict:
    """Return aggregate statistics about LLM assessment sessions."""
    conn = get_db_connection()

    total = conn.execute(
        'SELECT COUNT(*) as c FROM assessment_sessions'
    ).fetchone()['c']

    completed = conn.execute(
        "SELECT COUNT(*) as c FROM assessment_sessions WHERE status = 'COMPLETED'"
    ).fetchone()['c']

    mock_count = conn.execute(
        'SELECT COUNT(*) as c FROM assessment_sessions WHERE is_mock_mode = 1'
    ).fetchone()['c']

    avg_turns_row = conn.execute(
        "SELECT AVG(total_turns) as avg_t FROM assessment_sessions WHERE status = 'COMPLETED'"
    ).fetchone()
    avg_turns = round(avg_turns_row['avg_t'] or 0, 1)

    avg_duration_row = conn.execute(
        """SELECT AVG(interview_duration_sec) as avg_d 
           FROM assessment_sessions 
           WHERE status = 'COMPLETED' AND interview_duration_sec IS NOT NULL"""
    ).fetchone()
    avg_duration = round(avg_duration_row['avg_d'] or 0, 1)

    conn.close()

    return {
        "total_sessions": total,
        "completed_sessions": completed,
        "in_progress_sessions": total - completed,
        "mock_sessions": mock_count,
        "llm_sessions": total - mock_count,
        "avg_questions_per_session": avg_turns,
        "avg_interview_duration_sec": avg_duration,
    }
