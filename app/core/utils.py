from pathlib import Path

from runtime.manage_assets import init_db, import_json
from core.logger import get_logger
# from core.db.utils import fetch_asset_from_db, DB_FILE
# from core.smc.utils import smart_money_concept, ta_rsi, ta_mfi, ta_williams_r, ta_stoch

logger = get_logger(__name__)

TICKER_PATH = Path(__file__).parent / ".." / ".." / "runtime" / "ASSETS.json"

def update_data() -> None:
    # Update all ticker data and store it in local sqlite
    init_db()
    import_json(json_path=TICKER_PATH, do_update=True, delay=1.0)
    logger.info("Price data has been updated!")