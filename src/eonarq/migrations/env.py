from alembic import context


def run_migrations() -> None:
    connection = context.config.attributes.get("connection")
    if connection is None:
        raise RuntimeError("Run migrations with eonarq --init-db")
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
