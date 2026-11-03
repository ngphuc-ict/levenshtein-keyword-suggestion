import os

from algorithm import LevenshteinSuggester
from data_processor import DictionaryProcessor

dictionary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.txt")
suggester = LevenshteinSuggester()

# Kiểm tra khoảng cách chỉnh sửa
assert suggester.levenshtein_distance("kitten", "sitting") == 3
assert suggester.levenshtein_distance("", "abc") == 3
assert suggester.levenshtein_distance("áo", "áo") == 0

# Kiểm tra kết quả xếp hạng với từ điển thật
dictionary = DictionaryProcessor(dictionary_path).load_data()
results = suggester.rank_suggestions("điện thoại samsng", dictionary)

assert len(results) == 5
assert results[0].keyword == "điện thoại samsung"
assert all(
    results[i].distance <= results[i + 1].distance
    for i in range(len(results) - 1)
)

for item in results:
    print(f"{item.keyword} — khoảng cách {item.distance}")

print("Các kiểm tra đều đạt.")