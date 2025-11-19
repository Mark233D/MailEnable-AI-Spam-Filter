from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading, time, os, logging, json, sys
from app.model_loader import ModelLoader
from app.mail_handler import MailHandler
from app.storage import Storage

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_PATH = resource_path("config.json")
CONFIG = json.load(open(CONFIG_PATH, "r", encoding="utf-8"))

BASE_DIR = os.path.dirname(CONFIG_PATH)
LOG_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "spam_analyzer.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

model = ModelLoader(resource_path("models/spam_model_min.joblib"))
storage = Storage(resource_path("keys/fernet.key"), os.path.join(DATA_DIR, "consents.db"))
mail_handler = MailHandler(model, storage, CONFIG)

app = FastAPI(title="SpamAnalizör API")

class ConsentRequest(BaseModel):
    username: str
    provider: str
    imap_host: str | None = None
    imap_port: int | None = None
    imap_user: str | None = None
    imap_pass: str | None = None
    allow_auto_scan: bool = True

@app.post("/consent")
def consent(req: ConsentRequest):
    try:
        mail_handler.register_consent(
            req.username,
            req.provider,
            req.imap_host,
            req.imap_port,
            req.imap_user,
            req.imap_pass,
            req.allow_auto_scan
        )
        logging.info(f"Yeni izin eklendi: {req.username} ({req.provider})")
        return {"status": "ok"}
    except Exception as e:
        logging.exception("İzin kaydedilirken hata oluştu")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def status():
    return {"ok": True, "message": "SpamAnalizör API çalışıyor."}

def background_loop():
    interval = CONFIG.get("scan_interval_seconds", 60)
    logging.info(f"Arka plan tarayıcı başlatıldı (süre: {interval} sn)")
    while True:
        try:
            mail_handler.fetch_and_scan_for_all_consented_users()
        except Exception:
            logging.exception("Arka plan taramada hata oluştu")
        time.sleep(interval)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    logging.info("FastAPI başlatıldı ve tarayıcı thread çalışıyor.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,
                host=CONFIG.get("api_host", "127.0.0.1"),
                port=CONFIG.get("api_port", 8000))
