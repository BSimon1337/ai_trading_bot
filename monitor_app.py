from __future__ import annotations

from tradingbot.app.monitor import create_app


APP = create_app()


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8080, debug=False)
