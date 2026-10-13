from alembic import context
from app import create_app
from app.extensions import db
from app import models

app = create_app()
with app.app_context():
    if context.is_offline_mode():
        context.configure(url=app.config["SQLALCHEMY_DATABASE_URI"], target_metadata=db.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        with db.engine.connect() as conn:
            context.configure(connection=conn, target_metadata=db.metadata)
            with context.begin_transaction():
                context.run_migrations()
