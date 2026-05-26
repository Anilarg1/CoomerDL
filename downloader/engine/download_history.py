import sqlite3
import threading
from pathlib import Path


class DownloadHistory:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_url TEXT UNIQUE,
                    file_path TEXT,
                    file_size INTEGER,
                    user_id TEXT,
                    post_id TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.connection.commit()

    def contains(self, media_url: str) -> bool:
        return self.get(media_url) is not None

    def get(self, media_url: str) -> tuple[str, int] | None:
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT file_path, file_size FROM downloads WHERE media_url = ?", (media_url,))
            row = cursor.fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def record_completed(
        self,
        media_url: str,
        file_path: str,
        file_size: int,
        user_id: str | None = None,
        post_id: str | None = None,
    ):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO downloads (media_url, file_path, file_size, user_id, post_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (media_url, file_path, file_size, user_id, post_id),
            )
            self.connection.commit()

    def clear(self):
        with self.lock:
            self.connection.execute("DELETE FROM downloads")
            self.connection.commit()
