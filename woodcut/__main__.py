import signal
import sys

# 允许 `python -m woodcut ... | head` 这类管道正常关闭
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

from .cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
