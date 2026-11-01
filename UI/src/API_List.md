Method	Endpoint	                        Chức năng
GET	    /health	                            Kiểm tra backend
GET	    /search/suggest	                    Gợi ý trực tiếp
GET	    /search	                            Tìm kiếm từ khóa
GET	    /dictionary	                        Lấy danh sách từ
GET	    /dictionary/stats	                Thống kê từ điển
GET	    /algorithm/distance	                Tính khoảng cách chỉnh sửa
POST	/algorithm/visualize	            Lấy dữ liệu minh họa DP
POST	/benchmark/runs	Tạo                 benchmark
GET	    /benchmark/runs/{run_id}	        Lấy trạng thái/kết quả
GET	    /benchmark/runs/{run_id}/export	    Xuất kết quả CSV