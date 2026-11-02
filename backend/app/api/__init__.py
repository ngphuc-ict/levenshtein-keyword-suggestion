"""Gom các router của API.

Có hai nhóm:

``api_router`` (tiền tố ``/api/v1``)
    Hợp đồng gốc của backend: ``/suggest``, ``/health``, ``/stats``.
``contract_router`` (không tiền tố)
    Các đường dẫn mà frontend liệt kê trong ``UI/src/API_List.md``:
    ``/health``, ``/search/suggest``, ``/search``, ``/dictionary``,
    ``/dictionary/stats``, ``/algorithm/distance``, ``/algorithm/visualize``,
    ``/benchmark/runs``. Nhóm này gọi lại đúng logic của nhóm trên nên kết
    quả không bao giờ lệch nhau.
"""

from fastapi import APIRouter

from .algorithm import router as algorithm_router
from .benchmark import router as benchmark_router
from .dictionary import router as dictionary_router
from .search import router as search_router
from .suggest import router as suggest_router
from .system import root_router as system_root_router
from .system import router as system_router

api_router = APIRouter()
api_router.include_router(suggest_router)
api_router.include_router(system_router)

contract_router = APIRouter()
contract_router.include_router(system_root_router)
contract_router.include_router(search_router)
contract_router.include_router(dictionary_router)
contract_router.include_router(algorithm_router)
contract_router.include_router(benchmark_router)

__all__ = ["api_router", "contract_router"]
