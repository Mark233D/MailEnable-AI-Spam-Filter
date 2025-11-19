import joblib, os

class ModelLoader:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.load()

    def load(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(self.model_path)
        self.model = joblib.load(self.model_path)

    def predict_proba_text(self, text):
        if hasattr(self.model, "predict_proba"):
            p = float(self.model.predict_proba([text])[:,1][0])
            return p
        y = self.model.predict([text])[0]
        return 1.0 if int(y)==1 else 0.0
