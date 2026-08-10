"""
database.py
Database SQLite untuk TOD Telegram Bot.
"""

import sqlite3
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tod.db"


class Database:
    def __init__(self, path: Path):
        self.path = str(path)
        self.init()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    display_name TEXT NOT NULL,
                    games INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    created_by INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'lobby',
                    phase TEXT NOT NULL DEFAULT 'lobby',
                    current_loser INTEGER,
                    td_choice TEXT,
                    options_json TEXT DEFAULT '[]',
                    created_at INTEGER NOT NULL,
                    phase_started_at INTEGER NOT NULL,
                    round_no INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(chat_id, message_id)
                );

                CREATE TABLE IF NOT EXISTS room_players (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    joined_at INTEGER NOT NULL,
                    eliminated INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(chat_id, message_id, user_id),
                    FOREIGN KEY(chat_id, message_id)
                        REFERENCES rooms(chat_id, message_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS votes (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    round_no INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    option_index INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, message_id, round_no, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_rooms_status
                ON rooms(status);

                CREATE INDEX IF NOT EXISTS idx_room_players_room
                ON room_players(chat_id, message_id);
                """
            )

    def upsert_player(self, user_id: int, username: str, display_name: str):
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO players
                    (user_id, username, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    display_name=excluded.display_name,
                    updated_at=excluded.updated_at
                """,
                (user_id, username or "", display_name, now, now),
            )

    def get_player(self, user_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM players WHERE user_id=?",
                (user_id,),
            ).fetchone()

    def add_result(self, winner_id: Optional[int], loser_id: Optional[int]):
        now = int(time.time())
        with self.connect() as conn:
            if winner_id is not None and loser_id is not None:
                conn.execute(
                    """
                    UPDATE players
                    SET games=games+1, wins=wins+1, updated_at=?
                    WHERE user_id=?
                    """,
                    (now, winner_id),
                )
                conn.execute(
                    """
                    UPDATE players
                    SET games=games+1, losses=losses+1, updated_at=?
                    WHERE user_id=?
                    """,
                    (now, loser_id),
                )

    def add_draw(self, player_ids):
        now = int(time.time())
        with self.connect() as conn:
            for uid in player_ids:
                conn.execute(
                    """
                    UPDATE players
                    SET games=games+1, draws=draws+1, updated_at=?
                    WHERE user_id=?
                    """,
                    (now, uid),
                )

    def leaderboard(self, limit=10):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM players
                WHERE games > 0
                ORDER BY wins DESC,
                         (wins-losses) DESC,
                         games DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def create_room(
        self,
        chat_id: int,
        message_id: int,
        created_by: int,
        status="lobby",
        phase="lobby",
    ):
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rooms
                (chat_id, message_id, created_by, status, phase,
                 created_at, phase_started_at, round_no)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    chat_id,
                    message_id,
                    created_by,
                    status,
                    phase,
                    now,
                    now,
                ),
            )

    def get_room(self, chat_id, message_id):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM rooms
                WHERE chat_id=? AND message_id=?
                """,
                (chat_id, message_id),
            ).fetchone()

    def active_rooms(self):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM rooms
                WHERE status='active'
                """
            ).fetchall()

    def update_room(self, chat_id, message_id, **fields):
        if not fields:
            return

        allowed = {
            "status",
            "phase",
            "current_loser",
            "td_choice",
            "options_json",
            "phase_started_at",
            "round_no",
        }

        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return

        fields["phase_started_at"] = fields.get(
            "phase_started_at",
            int(time.time()),
        )

        sql = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())
        values.extend([chat_id, message_id])

        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE rooms
                SET {sql}
                WHERE chat_id=? AND message_id=?
                """,
                values,
            )

    def delete_room(self, chat_id, message_id):
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM rooms
                WHERE chat_id=? AND message_id=?
                """,
                (chat_id, message_id),
            )

    def add_player_to_room(
        self,
        chat_id,
        message_id,
        user_id,
        display_name,
    ):
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO room_players
                (chat_id, message_id, user_id, display_name, joined_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, message_id, user_id, display_name, now),
            )

    def room_players(self, chat_id, message_id):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM room_players
                WHERE chat_id=? AND message_id=?
                ORDER BY joined_at ASC
                """,
                (chat_id, message_id),
            ).fetchall()

    def active_room_for_user(self, user_id):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT r.*
                FROM rooms r
                JOIN room_players rp
                  ON rp.chat_id=r.chat_id
                 AND rp.message_id=r.message_id
                WHERE rp.user_id=?
                  AND r.status IN ('lobby','active')
                ORDER BY r.created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

    def set_eliminated(self, chat_id, message_id, user_id, value=1):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE room_players
                SET eliminated=?
                WHERE chat_id=? AND message_id=? AND user_id=?
                """,
                (value, chat_id, message_id, user_id),
            )

    def active_players(self, chat_id, message_id):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM room_players
                WHERE chat_id=? AND message_id=?
                  AND eliminated=0
                ORDER BY joined_at ASC
                """,
                (chat_id, message_id),
            ).fetchall()

    def save_vote(
        self,
        chat_id,
        message_id,
        round_no,
        user_id,
        option_index,
    ):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO votes
                (chat_id, message_id, round_no, user_id, option_index)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id, round_no, user_id)
                DO UPDATE SET option_index=excluded.option_index
                """,
                (
                    chat_id,
                    message_id,
                    round_no,
                    user_id,
                    option_index,
                ),
            )

    def get_votes(self, chat_id, message_id, round_no):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM votes
                WHERE chat_id=? AND message_id=? AND round_no=?
                """,
                (chat_id, message_id, round_no),
            ).fetchall()

    def clear_votes(self, chat_id, message_id, round_no):
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM votes
                WHERE chat_id=? AND message_id=? AND round_no=?
                """,
                (chat_id, message_id, round_no),
            )


DB = Database()
