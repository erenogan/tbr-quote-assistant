from concurrent.futures import ThreadPoolExecutor

from app.tools.add_to_quote import add_to_quote
from app.tools.get_quote import get_quote


def test_concurrent_duplicate_requests_increment_once():
    # Aynı key ile 5 kopya istek AYNI ANDA geliyor
    def send(_):
        return add_to_quote("Q-1001", "PRD-BC-110", 1, "storm-key", "msg-storm")

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(send, range(5)))

    assert sum(1 for r in results if not r["replayed"]) == 1  
    line = next(l for l in get_quote("Q-1001")["lines"] if l["status"] == "active")
    assert line["quantity"] == 2  