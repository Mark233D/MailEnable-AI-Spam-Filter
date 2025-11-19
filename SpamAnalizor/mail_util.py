import os
import sys
import time
import shutil
import logging
import ctypes
from email import policy
from email.parser import BytesParser

# ========== ADMİN YETKİSİ İŞLEMLERİ (YENİ EKLENDİ) ==========

def is_admin():
    """Sadece kontrol eder: Yönetici miyiz? (Evet/Hayır)"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def require_admin():
    """
    Yönetici izni yoksa, kullanıcıdan izin ister ve programı
    Yönetici olarak yeniden başlatır. Eski pencereyi kapatır.
    """
    if is_admin():
        # Zaten adminsek devam et
        return
    
    # Admin değilsek UAC penceresini tetikle
    print("[UYARI] Yonetici izni gerekiyor. Izin isteniyor...")
    try:
        # 'runas' parametresi Windows'ta "Yönetici Olarak Çalıştır" demektir
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # Yeni (yetkili) pencere açıldı, bu (yetkisiz) pencereyi kapat.
        sys.exit(0)
    except Exception as e:
        print(f"[HATA] Yonetici izni alinirken hata: {e}")
        return

# ========== GENEL UTILITY FONKSİYONLARI ==========

def wait_for_file(file_path, timeout=60):
    """Dosya hazır olana kadar bekle"""
    start = time.time()
    last_size = -1
    while time.time() - start < timeout:
        try:
            if os.path.exists(file_path):
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    return True
                last_size = current_size
        except (IOError, OSError):
            pass
        time.sleep(0.1)
    return False

def parse_mail(file_path):
    """Mail içeriğini oku"""
    try:
        with open(file_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        email_from = msg.get('From', 'Bilinmeyen Gönderen')
        subject = msg.get('Subject', 'Konu Yok')
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                    except: pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
            except: pass
        return email_from, subject, body
    except Exception as e:
        logging.error(f"[mail_util] Parse hatası ({os.path.basename(file_path)}): {e}")
        return "Hata", "Hata", ""

# ========== TAŞIMA İŞLEMLERİ ==========

def get_postoffice_root(mail_path):
    try:
        inbox_dir = os.path.dirname(mail_path)
        mail_root = os.path.dirname(inbox_dir)
        if os.path.basename(inbox_dir).lower() == 'inbox':
            return mail_root
        return mail_root
    except Exception as e:
        logging.error(f"[mail_util] PostOffice root hatasi: {e}")
        return None

def move_mail_to_deleted(mail_path, postoffice_root):
    try:
        if not os.path.exists(mail_path):
            return False, "Mail dosyasi bulunamadi"
        if not postoffice_root:
            return False, "PostOffice root yok"

        deleted_dir = os.path.join(postoffice_root, "Deleted Items")
        os.makedirs(deleted_dir, exist_ok=True) 

        filename = os.path.basename(mail_path)
        destination = os.path.join(deleted_dir, filename)
        
        if os.path.exists(destination):
            try: os.remove(destination) 
            except: pass

        shutil.move(mail_path, destination)
        return True, "Mail tasindi -> Deleted Items"
    except Exception as e:
        return False, f"Hata: {str(e)}"