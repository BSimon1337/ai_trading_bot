# systemd Deployment (Linux VM)

These units run:
- `tradingbot.py --mode live` (paper or live based on `.env`)
- `monitor_app.py` (dashboard on port `8080`)

## 1) Prepare repo on Linux

```bash
cd /absolute/path/to/repo
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt  # if you have one
```

If you do not have a single `requirements.txt`, install the packages your project uses (for example: `pandas`, `numpy`, `flask`, `gunicorn`, `joblib`, `xgboost`, `lumibot`, `alpaca-trade-api`, `python-dotenv`, `transformers`, `torch`).

## 2) Place environment file

The service expects:

```text
/absolute/path/to/repo/.env
```

If your current env file is `env/.env`, copy it:

```bash
cp env/.env .env
```

Suggested additional safety env vars:

```env
MAX_NOTIONAL_PER_ORDER_USD=10000
MAX_CONSECUTIVE_LOSSES=3
MAX_DATA_STALENESS_MINUTES=1440
```

## 3) Install services

```bash
chmod +x deploy/systemd/install_services.sh
./deploy/systemd/install_services.sh /absolute/path/to/repo your_linux_user
```

## 4) Check service status

```bash
systemctl status tradingbot.service --no-pager
systemctl status monitor.service --no-pager
```

## 5) View logs

```bash
journalctl -u tradingbot.service -f
journalctl -u monitor.service -f
```

## 6) Dashboard URL

```text
http://<vm-ip>:8080
```

Health endpoint:

```text
http://<vm-ip>:8080/health
```

## Optional hardening

- Put Nginx in front of `:8080`.
- Add basic auth and TLS if accessing outside LAN.
- Keep `PAPER_TRADING=true` until you complete paper validation.
- For containerized monitor-only deployment, see `deploy/docker/docker-compose.monitor.yml`.
