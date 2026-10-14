"""Run explicitly with the deployment's environment: python -m app.migrate."""

from app.config import get_settings
from app.repositories.sql import SqlRepositories
from app.agent.runtime import GraphResources


def main() -> None:
    settings = get_settings()
    if settings.storage_backend != "sql":
        raise SystemExit("Migration requires STORAGE_BACKEND=sql.")
    repositories = SqlRepositories(settings.database_url, initialize_schema=True)
    try:
        repositories.ready()
        from sqlalchemy.engine import make_url

        postgres = make_url(settings.database_url).get_backend_name() == "postgresql"
        resources = GraphResources(
            database_url=settings.database_url if postgres else None,
            path=None if postgres else settings.graph_checkpoint_path,
            schema=settings.graph_checkpoint_schema,
        )
        try:
            resources.ready()
        finally:
            resources.close()
    finally:
        repositories.close()
    print("Domain and checkpoint migrations complete.")


if __name__ == "__main__":
    main()
