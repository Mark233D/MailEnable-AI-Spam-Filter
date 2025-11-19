import os
import sys
import logging
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests

# UTILITY MODÜLÜNDEN ÇEKİYORUZ
try:
    from mail_util import (
        move_mail_to_deleted, 
        get_postoffice_root, 
        wait_for_file, 
        parse_mail, 
        require_admin  # <-- YENİ EKLENEN
    )
except ImportError:
    print("KRITIK HATA: mail_util.py bulunamadi!")
    sys.exit(1)

# ========== DİNAMİK YOLLAR ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
TRACKING_FILE = os.path.join(BASE_DIR, "processed_tracker.json")
LOG_FILE = os.path.join(BASE_DIR, "mail_watchdog.log")

# ========== AYARLARI YÜKLE ==========
def load_config():
    defaults = {
        "WATCH_DIR": r"C:\Program Files (x86)\Mail Enable\Postoffices",
        "API_URL": "http://127.0.0.1:8000/conclusion",
        "TRACKING_EXPIRY": 10
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**defaults, **json.load(f)}
        except: pass
    return defaults

CONFIG = load_config()
WATCH_DIR = CONFIG["WATCH_DIR"]
API_URL = CONFIG["API_URL"]
TRACKING_EXPIRY = CONFIG["TRACKING_EXPIRY"]

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)

# ========== TRACKER İŞLEMLERİ ==========
def is_processed(filename):
    try:
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                data = json.load(f)
                if filename in data and (time.time() - data[filename] < TRACKING_EXPIRY):
                    return True
    except: pass
    return False

def mark_processed(filename):
    try:
        data = {}
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                data = json.load(f)
        data[filename] = time.time()
        with open(TRACKING_FILE, 'w') as f:
            json.dump(data, f)
    except: pass

def send_to_api(text):
    try:
        response = requests.post(API_URL, json={"text": text}, timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logging.error(f"API hatasi: {e}")
        return None

# ========== WATCHDOG HANDLER ==========
class MailHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.upper().endswith('.MAI'): return
        
        filename = os.path.basename(event.src_path)
        if is_processed(filename): return
        
        logging.info(f"📧 Mail bulundu: {filename}")
        
        if not wait_for_file(event.src_path):
            mark_processed(filename)
            return
        
        email_from, subject, body = parse_mail(event.src_path)
        
        if not subject and not body:
            mark_processed(filename)
            return
            
        result = send_to_api(f"{subject} {body}")
        
        if result:
            is_prob = result.get("is_problematic", False)
            reasons = result.get("reasons", [])
            log_details = f"Kimden: {email_from} | Dosya: {filename}"

            if is_prob:
                logging.warning(f"🗑️ SORUNLU -> {log_details} | Neden: {reasons}")
                root = get_postoffice_root(event.src_path)
                if root:
                    success, msg = move_mail_to_deleted(event.src_path, root)
                    if success: logging.info("   ✅ TASIMA BASARILI")
                    else: logging.error(f"   ❌ TASIMA HATASI: {msg}")
            else:
                logging.info(f"✅ TEMIZ -> {log_details}")
        
        mark_processed(filename)

# ========== MAIN ==========
def main():
    # MODÜLDEN ÇAĞRILAN YETKİ KONTROLÜ
    # Bu satır, eğer admin değilse programı yeniden başlatır.
    require_admin()

    if not os.path.exists(WATCH_DIR):
        logging.warning(f"⚠️ Watch dizini bulunamadi: {WATCH_DIR}")

    logging.info(f"🟢 MailPrep Watchdog Baslatildi (Yonetici Modu) | Hedef: {WATCH_DIR}")
    
    observer = Observer()
    observer.schedule(MailHandler(), WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while True: time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()