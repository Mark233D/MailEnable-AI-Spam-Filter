import imaplib, email, logging
from email.header import decode_header

class MailHandler:
    def __init__(self, model_loader, storage, config):
        self.model = model_loader
        self.storage = storage
        self.config = config

    def register_consent(self, username, provider, imap_host, imap_port, imap_user, imap_pass, allow=True):
        if not imap_host:
            prov = self.config["providers"].get(provider)
            if prov:
                imap_host = prov["imap_host"]
                imap_port = prov.get("port", 993)
        self.storage.save_consent(username, provider, imap_host, imap_port, imap_user, imap_pass, allow)

    def fetch_and_scan_for_all_consented_users(self):
        for acct in self.storage.get_all_consented():
            try:
                self._scan_account(acct)
            except Exception:
                logging.exception("Tarama hatası: %s", acct.get("username"))

    def _scan_account(self, acct):
        host, port, user, pwd = acct["host"], acct["port"], acct["user"], acct["pass"]
        if not host or not user or not pwd:
            logging.warning("Eksik bilgi: %s", acct["username"])
            return

        logging.info("IMAP bağlantısı: %s@%s:%s", user, host, port)
        M = imaplib.IMAP4_SSL(host, port)
        M.login(user, pwd)
        M.select("INBOX")
        typ, data = M.search(None, 'UNSEEN')
        if typ != 'OK':
            logging.warning("Mail araması başarısız: %s", acct["username"])
            M.logout(); return

        for num in data[0].split():
            typ, msg_data = M.fetch(num, '(RFC822)')
            if typ != 'OK' or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = self._decode_header(msg.get("Subject"))
            body = self._get_body_text(msg)
            text = (subject or "") + "\n" + (body or "")
            prob = self.model.predict_proba_text(text)
            logging.info("%s mesaj %s spam_olasılık=%.3f", acct["username"], num.decode() if isinstance(num, bytes) else num, prob)
            if prob >= self.config.get("spam_threshold", 0.65):
                self._move_to_junk(M, num)
        M.logout()

    def _decode_header(self, h):
        if not h: return ""
        parts = decode_header(h)
        out = ""
        for part, enc in parts:
            if isinstance(part, bytes):
                out += part.decode(enc or "utf-8", errors="ignore")
            else:
                out += part
        return out

    def _get_body_text(self, msg):
        if msg.is_multipart():
            for p in msg.walk():
                if p.get_content_type() == "text/plain" and p.get_content_disposition() is None:
                    return p.get_payload(decode=True).decode(errors="ignore")
        else:
            return msg.get_payload(decode=True).decode(errors="ignore")

    def _move_to_junk(self, imap_conn, msgnum):
        try:
            imap_conn.copy(msgnum, "Junk")
            imap_conn.store(msgnum, "+FLAGS", "\\Deleted")
            imap_conn.expunge()
            logging.info("Mesaj Junk'a taşındı: %s", msgnum)
        except Exception:
            logging.exception("Junk'a taşıma hatası: %s", msgnum)
