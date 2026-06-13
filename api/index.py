"""Read-only Vercel adapter for the local event automation console."""

from scripts.console_server import ConsoleHandler


class handler(ConsoleHandler):
    def do_POST(self) -> None:
        self.send_json(
            {
                "ok": False,
                "error": "이 작업은 로컬 콘솔에서만 실행할 수 있습니다.",
                "localOnly": True,
            },
            503,
        )
