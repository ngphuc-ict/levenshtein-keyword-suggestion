import re
import unicodedata
import os

class DictionaryProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.dictionary = set()

    def normalize_text(self, text):
        if not text:
            return ""
        text = unicodedata.normalize('NFC', text) # Chuẩn hóa bảng mã tiếng Việt
        text = text.lower() # Chữ thường
        text = re.sub(r'[^\w\s]', '', text) # Bỏ dấu câu
        text = re.sub(r'\s+', ' ', text).strip() # Gộp khoảng trắng thừa
        return text

    def load_data(self):
        if not os.path.exists(self.file_path):
            print(f"[Lỗi] Không tìm thấy: {self.file_path}")
            return []

        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                cleaned = self.normalize_text(line)
                if cleaned:
                    self.dictionary.add(cleaned)
                    
        return list(self.dictionary)

# Test thử:
if __name__ == "__main__":
    processor = DictionaryProcessor('dictionary.txt')
    data = processor.load_data()
    print(f"Sẵn sàng đưa {len(data)} từ khóa vào thuật toán Levenshtein.")