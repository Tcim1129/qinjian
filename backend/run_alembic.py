import sys
from alembic.config import Config
from alembic import command

def migrate():
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, autogenerate=True, message="Add agent chat models")
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    migrate()
    print("Agent Chat Models Migration Completed Successfully.")
