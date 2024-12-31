from alembic import command
from alembic.config import Config

from open_webui.env import OPEN_WEBUI_DIR

alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")

# Set the script location dynamically
migrations_path = OPEN_WEBUI_DIR / "migrations"
alembic_cfg.set_main_option("script_location", str(migrations_path))


def upgrade() -> None:
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    upgrade()
