# Gợi ý từ khóa bằng Quy hoạch động

Bài tập giữa kỳ môn **Phân tích và Thiết kế Giải thuật**: xây dựng chức năng gợi ý từ khóa khi người dùng nhập sai chính tả, dựa trên khoảng cách chỉnh sửa chuỗi **Levenshtein** và kỹ thuật **Quy hoạch động (Dynamic Programming)**.

## Mục tiêu

Nhận một từ khóa tìm kiếm, so sánh với các từ trong từ điển và trả về tối đa 5 từ khóa gần nhất. Khoảng cách Levenshtein là số phép chèn, xóa hoặc thay thế ký tự ít nhất để biến chuỗi này thành chuỗi kia. Khoảng cách càng nhỏ thì hai chuỗi càng gần nhau về mặt ký tự.

> Đây là thuật toán so khớp chuỗi theo ký tự; nó không hiểu ngữ nghĩa của sản phẩm.

## Cấu trúc hiện tại

- algorithm.py: lớp LevenshteinSuggester, chuẩn hóa truy vấn, tính khoảng cách bằng quy hoạch động và xếp hạng gợi ý.
- data_processor.py: lớp DictionaryProcessor đọc từ điển UTF-8, chuẩn hóa chuỗi và loại bỏ từ khóa trùng lặp.
- dictionary.txt: từ khóa sản phẩm tiếng Việt, mỗi từ khóa nằm trên một dòng. Tệp hiện có khoảng 23.850 dòng.

## Yêu cầu

- Python 3.7 trở lên.
- Không cần cài thư viện bên ngoài; thuật toán chỉ dùng thư viện chuẩn của Python.

## Chạy thử

Mở Terminal hoặc PowerShell tại thư mục dự án. Tạo tệp demo.py với nội dung sau:

    from algorithm import LevenshteinSuggester
    from data_processor import DictionaryProcessor

    # Đọc từ điển một lần và tái sử dụng cho các lần tìm kiếm.
    dictionary = DictionaryProcessor("dictionary.txt").load_data()
    suggester = LevenshteinSuggester()

    query = "điện thoại samsng"
    for item in suggester.rank_suggestions(query, dictionary, limit=5):
        print(f"{item.keyword} — khoảng cách {item.distance}")

Chạy chương trình:

    python demo.py

Trên Windows, nếu lệnh python không khả dụng, có thể thử:

    py -3 demo.py

Với truy vấn mẫu trên, điện thoại samsung có khoảng cách 1 vì chỉ cần thêm ký tự u. Các từ khóa tiếp theo được xếp theo khoảng cách; khi khoảng cách bằng nhau, chúng được xếp theo thứ tự chữ cái để kết quả ổn định.

## Dùng thuật toán trong Service

    from algorithm import LevenshteinSuggester

    suggester = LevenshteinSuggester()

    # dictionary là danh sách từ khóa đã tải bằng DictionaryProcessor.
    keywords = suggester.suggest(query, dictionary, limit=5)

    # Hoặc lấy cả khoảng cách để hiển thị/ghi nhận trong giao diện.
    ranked = suggester.rank_suggestions(query, dictionary, limit=5)
    for item in ranked:
        print(item.keyword, item.distance)

Nên tải từ điển một lần khi khởi động service, sau đó truyền danh sách đó vào mỗi lần gợi ý. suggest trả về danh sách chuỗi; rank_suggestions trả về các đối tượng Suggestion có hai thuộc tính keyword và distance.

## Kiểm tra nhanh

Có thể chạy các kiểm tra cơ bản bằng cách tạo tệp check_algorithm.py:

    from algorithm import LevenshteinSuggester

    suggester = LevenshteinSuggester()
    assert suggester.levenshtein_distance("kitten", "sitting") == 3
    assert suggester.levenshtein_distance("", "abc") == 3
    assert suggester.levenshtein_distance("áo", "áo") == 0
    print("Các kiểm tra đều đạt.")

Chạy bằng python check_algorithm.py.

## Chuẩn hóa và tiếng Việt

Thuật toán chuẩn hóa Unicode về NFC, chuyển thành chữ thường, bỏ dấu câu và gộp khoảng trắng. Dấu tiếng Việt được giữ nguyên. Vì khoảng cách được tính trực tiếp trên ký tự Unicode, truy vấn có dấu thường phù hợp hơn với từ điển có dấu; ví dụ dùng điện thoại samsng thay vì dien thoai samsng.

## Ghi chú hiệu năng

Với mỗi từ khóa trong từ điển, thuật toán tính khoảng cách trong thời gian O(m × n), với m và n là độ dài hai chuỗi. Quy hoạch động chỉ giữ hai hàng kết quả, nên bộ nhớ cho mỗi lần tính khoảng cách là O(min(m, n)). Việc quét toàn bộ từ điển được thực hiện cho mỗi truy vấn. Cần đo thời gian trên máy chạy demo để báo cáo tốc độ thực tế.

## Phân công dự kiến

- **Thuật toán:** algorithm.py — Levenshtein bằng quy hoạch động và xếp hạng Top 5.
- **Dữ liệu:** dictionary.txt, data_processor.py — từ điển và xử lý đầu vào.
- **Backend / Service:** ghép bộ đọc từ điển với utility, xây dựng luồng xử lý và unit test.
- **UI / Báo cáo:** giao diện demo, benchmark và slide thuyết trình.
