import os
from pathlib import Path
from loguru import logger
import sqlite3
from threading import Lock

DEFAULT_PATH = os.path.join(
    Path(os.path.dirname(os.path.realpath(__file__))).parent, "data", "searcharr.db"
)


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class Database:
    lock = Lock()
    db_file: Path
    file: str

    def _get_con_cur(self):
        # Connect to local DB and return tuple containing connection and cursor
        try:
            con = sqlite3.connect(self.db_file, timeout=30)
            con.execute("PRAGMA journal_mode = off;")
            con.row_factory = _dict_factory
            cur = con.cursor()
            logger.debug(f"Database connection established [{self.db_file}].")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

        return (con, cur)

    def __init__(self, db_file=DEFAULT_PATH):
        self.db_file = Path(db_file)
        # Make sure the file exists
        self.db_file.parent.mkdir(exist_ok=True, parents=True)
        self.db_file.touch(exist_ok=True)
        # Initialize the db
        self._init_db()

    def _init_db(self):
        con, cur = self._get_con_cur()
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id integer primary key,
                username text not null,
                auth_level integer
            );""",
        ]
        for q in queries:
            logger.debug(f"Executing query: [{q}] with no args...")
            try:
                with self.lock:
                    cur.execute(q)
            except sqlite3.Error as e:
                logger.error(f"Error executing database query [{q}]: {e}")
                raise

        con.commit()
        con.close()

    def _execute_query(self, q, qa=()):
        con, cur = self._get_con_cur()
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with self.lock:
                r = cur.execute(q, qa)
                return (r, con)
        except sqlite3.Error as e:
            logger.error(f"Error executing database query [{q}]: {e}")
            raise

    def add_user(self, id, username, auth_level):
        q = "INSERT OR REPLACE INTO users (id, username, auth_level) VALUES (?, ?, ?);"
        qa = (id, username, auth_level)
        (_, con) = self._execute_query(q, qa)
        con.commit()
        con.close()

    def remove_user(self, id):
        q = "DELETE FROM users where id=?;"
        qa = (id,)
        (_, con) = self._execute_query(q, qa)
        con.commit()
        con.close()

    def get_users(
        self,
        auth_level=None,
        min_auth_level=None,
    ):
        auth_check = (
            f">= {min_auth_level}"
            if min_auth_level
            else f"== {auth_level}" if auth_level else ""
        )
        q = f"SELECT * FROM users where auth_level {auth_check}"
        (r, con) = self._execute_query(q)
        records = r.fetchall() if r else []
        logger.debug(f"Found {len(records)} users in the database.")
        con.close()
        return records

    def update_auth_level(self, user_id, auth_level=1):
        q = "UPDATE users set auth_level=? where id=?;"
        qa = (auth_level, user_id)
        (_, con) = self._execute_query(q, qa)
        con.commit()
        con.close()

    def get_auth_level(self, user_id):
        q = "SELECT * FROM users WHERE id=?;"
        qa = (user_id,)
        (r, con) = self._execute_query(q, qa)

        record = r.fetchone() if r else None
        logger.debug(f"Query result for user lookup: {record}")
        con.close()
        if record and record["id"] == user_id:
            return record["auth_level"]

        logger.debug(f"Did not find user [{user_id}] in the database.")
        return None
