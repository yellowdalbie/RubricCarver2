import sqlite3
import json
import os
from datetime import datetime


class ExperimentDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS cycles (
            cycle_id INTEGER PRIMARY KEY,
            cycle_name TEXT UNIQUE,
            timestamp TEXT,
            rubric_content TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS teacher_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            student_id TEXT,
            teacher_id TEXT,
            checklist_data TEXT,   -- JSON: {C1-1: {answer, basis}, ...}
            element_scores TEXT,   -- JSON: {요소1: N, 요소2: N, 요소3: N} (코드 계산)
            total INTEGER,         -- 코드 계산값
            level TEXT,
            comment TEXT,
            UNIQUE(cycle_id, student_id, teacher_id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS cycle_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            revision INTEGER,
            proposal TEXT,
            decision TEXT,
            status TEXT
        )''')

        conn.commit()
        conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_cycle(self, cycle_name, rubric_content):
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute('SELECT cycle_id FROM cycles WHERE cycle_name = ?', (cycle_name,))
            row = c.fetchone()
            if row:
                return row[0]
            c.execute('INSERT INTO cycles (cycle_name, timestamp, rubric_content) VALUES (?, ?, ?)',
                      (cycle_name, datetime.now().isoformat(), rubric_content))
            rowid = c.lastrowid
            conn.commit()
            return rowid
        finally:
            conn.close()

    def check_grade_exists(self, cycle_id, student_id, teacher_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT 1 FROM teacher_grades WHERE cycle_id=? AND student_id=? AND teacher_id=?',
                  (cycle_id, student_id, teacher_id))
        result = c.fetchone()
        conn.close()
        return result is not None

    def add_teacher_grade(self, cycle_id, student_id, teacher_id,
                          checklist_json, element_scores_json, total, level, comment):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO teacher_grades
                     (cycle_id, student_id, teacher_id,
                      checklist_data, element_scores, total, level, comment)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (cycle_id, student_id, teacher_id,
                   checklist_json, element_scores_json, total, level, comment))
        conn.commit()
        conn.close()

    def add_cycle_result(self, cycle_id, revision, proposal, decision, status):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO cycle_results (cycle_id, revision, proposal, decision, status) VALUES (?, ?, ?, ?, ?)',
                  (cycle_id, revision, proposal, decision, status))
        conn.commit()
        conn.close()

    def get_cycle_checklist_data(self, cycle_id):
        """분석관용: 이진 채점표 전체 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''SELECT student_id, teacher_id, checklist_data, total, level, comment
                     FROM teacher_grades WHERE cycle_id=?
                     ORDER BY student_id, teacher_id''', (cycle_id,))
        rows = c.fetchall()
        conn.close()
        return rows
