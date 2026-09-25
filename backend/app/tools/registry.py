"""Tek kapı: bütün tool çağrıları buradan geçer ve burada loglanır.

Tool'ları doğrudan çağırmak yerine ToolRunner.call() kullanılır. Böylece:
- her çağrı sıra numarası alır,
- her çağrı (başarılı ya da hatalı) tool_call_logs'a yazılır,
- hiçbir tool log'u "unutamaz", çünkü log tool'un içinde değil kapıda.
"""
from dataclasses import dataclass, field
from typing import Callable

from app.db import pool
from app.tools.add_to_quote import add_to_quote
from app.tools.common import to_jsonb
from app.tools.errors import ToolError
from app.tools.get_knowledge_entries import get_knowledge_entries
from app.tools.get_quote import get_quote
from app.tools.replace_with_alternative import replace_with_alternative
from app.tools.search_products import search_products
from app.tools.update_quote_item import update_quote_item

TOOLS = {
    "search_products": search_products,
    "get_knowledge_entries": get_knowledge_entries,
    "get_quote": get_quote,
    "add_to_quote": add_to_quote,
    "update_quote_item": update_quote_item,
    "replace_with_alternative": replace_with_alternative,
}
MUTATIONS = {"add_to_quote", "update_quote_item", "replace_with_alternative"}


_HIDDEN_INPUTS = {"idempotency_key", "source_message_id"}


def summarize_input(kwargs: dict) -> dict:
    """Kullanıcıya gösterilecek kısa girdi özeti (teknik anahtarlar gizlenir, boşlar atılır)."""
    return {k: str(v) for k, v in kwargs.items() if k not in _HIDDEN_INPUTS and v not in (None, [], "")}


@dataclass
class ToolCallResult:
    seq: int
    tool_name: str
    input: dict
    status: str                      # "success" | "error"
    output: dict | None = None
    error: dict | None = None        # {"code": ..., "message": ...}

    @property
    def ok(self) -> bool:
        return self.status == "success"

    @property
    def is_mutation(self) -> bool:
        return self.tool_name in MUTATIONS


@dataclass
class ToolRunner:
    """Bir kullanıcı mesajı boyunca yapılan tool çağrılarını yürütür ve loglar."""
    session_id: str | None = None
    message_id: str | None = None
    on_event: Callable[[dict], None] | None = None   # SSE: tool_start / tool_result
    calls: list[ToolCallResult] = field(default_factory=list)

    def _emit(self, event: dict) -> None:
        if self.on_event:
            self.on_event(event)

    def call(self, tool_name: str, **kwargs) -> ToolCallResult:
        if tool_name not in TOOLS:
            raise ValueError(f"Bilinmeyen tool: {tool_name}")
        seq = len(self.calls) + 1
        self._emit({"type": "tool_start", "seq": seq, "tool": tool_name,
                    "input_summary": summarize_input(kwargs)})

        try:
            output = TOOLS[tool_name](**kwargs)
            result = ToolCallResult(seq, tool_name, kwargs, "success", output=output)
        except ToolError as e:
            # Bilinen, kontrollü hata (limit aşıldı, stok yok...). Fırlatmıyoruz:
            # router bunu kullanıcıya Türkçe açıklayacak.
            result = ToolCallResult(seq, tool_name, kwargs, "error",
                                    error={"code": e.code, "message": e.message})
        except Exception as e:
            # Beklenmedik hata (bug). Yine de logla, sonra yukarı fırlat.
            self._log(ToolCallResult(seq, tool_name, kwargs, "error",
                                     error={"code": "internal_error", "message": str(e)}))
            raise

        self._log(result)
        self.calls.append(result)
        self._emit({
            "type": "tool_result", "seq": seq, "tool": tool_name, "status": result.status,
            "quote_delta": result.output.get("delta") if result.ok and result.is_mutation else None,
            "error": result.error,
        })
        return result

    def _log(self, result: ToolCallResult) -> None:
        # AYRI transaction: tool'un kendi transaction'ı çoktan bitti (commit ya da
        # rollback). Mutasyon geri alınmış olsa bile bu kayıt kalıcı olur.
        with pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO tool_call_logs
                    (session_id, message_id, seq, tool_name, input, status, output)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (self.session_id, self.message_id, result.seq, result.tool_name,
                 to_jsonb(result.input), result.status,
                 to_jsonb(result.output if result.ok else result.error)),
            )

    @property
    def tool_names(self) -> list[str]:
        return [c.tool_name for c in self.calls]
