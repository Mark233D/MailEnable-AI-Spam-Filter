import sqlite3, os
from cryptography.fernet import Fernet

class Storage:
    def __init__(self, key_path, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.key = self._load_or_create_key(key_path)
        self.f = Fernet(self.key)
        self.db_path = db_path
        self._ensure_db()

    def _load_or_create_key(self, path):
        if os.path.exists(path):
            return open(path, "rb").read()
        k = Fernet.generate_key()
        open(path, "wb").write(k)
        return k

    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS consents(
            username TEXT PRIMARY KEY,
            provider TEXT,
            imap_host TEXT,
            imap_port INTEGER,
            imap_user TEXT,
            imap_pass_enc BLOB,
            allow_auto_scan INTEGER
        )""")
        conn.commit(); conn.close()

    def save_consent(self, username, provider, imap_host, imap_port, imap_user, imap_pass, allow):
        enc = self.f.encrypt(imap_pass.encode()) if imap_pass else None
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""INSERT OR REPLACE INTO consents
                       (username, provider, imap_host, imap_port, imap_user, imap_pass_enc, allow_auto_scan)
                       VALUES(?,?,?,?,?,?,?)""",
                    (username, provider, imap_host, imap_port, imap_user, enc, 1 if allow else 0))
        conn.commit(); conn.close()

    def get_all_consented(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT username, provider, imap_host, imap_port, imap_user, imap_pass_enc FROM consents WHERE allow_auto_scan=1")
        rows = cur.fetchall(); conn.close()
        for username, provider, host, port, user, enc in rows:
            pwd = self.f.decrypt(enc).decode() if enc else None
            yield {"username": username, "provider": provider, "host": host, "port": port, "user": user, "pass": pwd}
