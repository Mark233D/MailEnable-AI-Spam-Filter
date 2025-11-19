import os
import sys
import logging
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jpype import *
import jpype.imports

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('api_server.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI()

# ========== DOSYA YOLLARI (PATH SETUP) ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== ZEMBEREK BASLATMA ==========
if not jpype.isJVMStarted():
    jar_path = os.path.join(BASE_DIR, "zemberek-full.jar")
    if not os.path.exists(jar_path):
        logging.error(f"Zemberek dosyasi bulunamadi: {jar_path}")
    startJVM(classpath=[jar_path])

from jpype.types import *
JClass = jpype.JClass
TurkishMorphology = JClass("zemberek.morphology.TurkishMorphology")

try:
    builder = TurkishMorphology.builder()
    morphology = builder.build()
    logging.info("Zemberek baslatildi")
except Exception as e:
    logging.error(f"Zemberek hatasi: {e}")

# ========== BANNED WORDS YUKLEME ==========
BANNED_WORDS_FILE = os.path.join(BASE_DIR, "bannedwords.txt")

def load_banned_words():
    try:
        if not os.path.exists(BANNED_WORDS_FILE):
            logging.warning(f"Banned words dosyasi bulunamadi: {BANNED_WORDS_FILE}")
            return set()
        with open(BANNED_WORDS_FILE, 'r', encoding='utf-8') as f:
            banned = set(line.strip().lower() for line in f if line.strip())
            logging.info(f"Banned words yuklendi: {len(banned)} kelime")
            return banned
    except Exception as e:
        logging.error(f"Banned words yukleme hatasi: {e}")
        return set()

BANNED_WORDS = load_banned_words()

# ========== MODEL YUKLEME ==========
MODEL_PATH = os.path.join(BASE_DIR, 'spam_model_min.joblib')

try:
    spam_pipeline = joblib.load(MODEL_PATH)
    logging.info(f"Model yuklendi: {MODEL_PATH}")
except Exception as e:
    logging.error(f"Model yukleme hatasi: {e}")
    spam_pipeline = None

# ========== ANALIZ FONKSİYONLARI ==========

def get_root(word):
    word = word.lower().strip(".,!?;:-")
    turkish_suffixes = [
        'larımızda', 'larınızda', 'larında', 'lerinde', 'larımdan', 'larınızdan', 
        'larından', 'lerinden', 'larımız', 'larınız', 'larının', 'lerinin', 
        'larmış', 'lermişler', 'larmıştı', 'lermişti', 'tirmişsin', 'tirmişsiniz', 
        'tirmişler', 'tirmişim', 'termişsin', 'termişsiniz', 'termişler', 'termişim', 
        'mışsın', 'mışsiniz', 'mışlar', 'mışım', 'ydun', 'ydın', 'ydım', 'ydı', 'ydu', 
        'tiydu', 'tidim', 'tiniz', 'tiyim', 'ları', 'leri', 'lar', 'ler', 'ımız', 
        'iniz', 'ının', 'lerinin', 'ım', 'in', 'ı', 'i', 'ımızı', 'inizi', 'unuz', 
        'ünüz', 'ınız', 'iniz', 'miş', 'mişsin', 'miştim', 'miştiniz', 'mişler', 
        'muş', 'müş', 'tiydi', 'tiyse', 'tidim', 'tiniz', 'ti', 'tı', 'tu', 'tü', 
        'di', 'dı', 'du', 'dü', 'me', 'ma', 'yecek', 'yacak', 'iyor', 'uyor', 'ıyor', 
        'üyor', 'ıyorum', 'iyorum', 'iyorum', 'üyorum', 'sin', 'sun', 'sün', 'siniz', 
        'sunuz', 'sünüz', 'yim', 'yi', 'niz', 'nuz', 'nüz', 'de', 'da', 'den', 'dan', 
        'e', 'a', 'u', 'ü', 'ile', 'yile',
    ]
    original_word = word
    for suffix in sorted(turkish_suffixes, key=len, reverse=True):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            root = word[:-len(suffix)]
            if len(root) >= 2:
                word = root
                return get_root(word) if word != original_word else word
    return word

def check_banned_words(text):
    found_banned = []
    words = text.lower().split()
    for word in words:
        clean_word = word.strip(".,!?;:-")
        if clean_word in BANNED_WORDS:
            found_banned.append({"word": clean_word, "type": "exact"})
            continue
        root = get_root(clean_word)
        if root in BANNED_WORDS and root != clean_word:
            found_banned.append({"word": clean_word, "root": root, "type": "stem"})
    return found_banned

def analyze_spam(text):
    if not spam_pipeline:
        return {"is_spam": False, "score": 0.0}
    try:
        prediction = spam_pipeline.predict([text])[0]
        probability = spam_pipeline.predict_proba([text])[0]
        spam_score = float(probability[1])
        return {"is_spam": bool(prediction), "score": spam_score}
    except Exception as e:
        logging.error(f"ML analiz hatasi: {e}")
        return {"is_spam": False, "score": 0.0}

def analyze_mail(text: str):
    try:
        curse_result_list = check_banned_words(text)
        has_curse = len(curse_result_list) > 0
        
        spam_result_dict = analyze_spam(text)
        is_spam = spam_result_dict["is_spam"]
        
        is_problematic = has_curse or is_spam
        
        reasons = []
        if has_curse:
            reasons.append(f"Yasak kelime: {len(curse_result_list)} kelime")
        if is_spam:
            reasons.append(f"Spam (skor: {spam_result_dict['score']:.2%})")
        if not is_problematic:
            reasons.append("Temiz")
            
        logging.info(f"Analiz sonucu: problematic={is_problematic} | Text: {text[:60]}...")
            
        return {
            "is_problematic": is_problematic,
            "reasons": reasons,
            "curse_details": {
                "has_curse": has_curse,
                "found_words": curse_result_list
            },
            "spam_details": {
                "is_spam": is_spam,
                "score": spam_result_dict["score"]
            }
        }
    
    except Exception as e:
        logging.error(f"Analiz hatasi: {e}")
        raise Exception(f"Analiz hatasi: {str(e)}")

# ========== API ENDPOINTS ==========

class AnalysisRequest(BaseModel):
    text: str

@app.post("/check-curse")
async def check_curse(request: AnalysisRequest):
    found = check_banned_words(request.text)
    return {
        "text": request.text[:100],
        "has_curse": len(found) > 0,
        "banned_words_found": found,
        "curse_score": len(found) * 10
    }

@app.post("/analyze-spam")
async def analyze_spam_endpoint(request: AnalysisRequest):
    ml_result = analyze_spam(request.text)
    final_score = min(ml_result["score"], 1.0)
    
    return {
        "text": request.text[:100],
        "is_spam": final_score > 0.5,
        "spam_score": final_score
    }

@app.post("/conclusion")
async def conclusion(request: AnalysisRequest):
    try:
        result = analyze_mail(request.text)
        return result
    except Exception as e:
        logging.error(f"Endpoint hatasi: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucu hatasi: {str(e)}")

@app.get("/")
async def root():
    return {
        "name": "Mail Analyzer API",
        "version": "3.0",
        "status": "online",
        "endpoints": {
            "GET /": "API bilgisi",
            "GET /health": "Saglik kontrolu",
            "POST /check-curse": "Kufur kontrolu",
            "POST /analyze-spam": "Spam analizi",
            "POST /conclusion": "Tam analiz"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "online",
        "banned_words_loaded": len(BANNED_WORDS) > 0,
        "model_loaded": spam_pipeline is not None,
        "banned_words_count": len(BANNED_WORDS)
    }

if __name__ == "__main__":
    import uvicorn
    print("Mail Analyzer API baslatiliyor...")
    uvicorn.run(app, host="127.0.0.1", port=8000)