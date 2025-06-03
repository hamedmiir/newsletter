from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auto_journalist.models import Base
from auto_journalist.config import DATABASE_URL

def run_migrations_online():
    config = context.config
    fileConfig(config.config_file_name)
    connectable = engine_from_config(
        {'sqlalchemy.url': DATABASE_URL},
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

def run_migrations_offline():
    raise NotImplementedError("Offline migrations not supported")

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()