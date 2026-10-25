from dataclasses import dataclass

from dature import EnvSource, load
from sqlalchemy.engine import make_url


@dataclass(frozen=True, slots=True)
class Config:
    DATABASE_URL: str = "sqlite:///./data/eonarq.sqlite3"
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    ALLOWED_HOSTS: str = "localhost;127.0.0.1;[::1]"

    def __post_init__(self) -> None:
        """Validate construction before the object is used."""
        if not self.DATABASE_URL.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL must use synchronous sqlite:///")
        url = make_url(self.DATABASE_URL)
        if (
            not url.database
            or ":memory:" in url.database
            or url.query.get("mode") == "memory"
        ):
            raise ValueError("DATABASE_URL must name a persistent SQLite file")
        if not self.HOST or not 1 <= self.PORT <= 65535:
            raise ValueError("HOST and PORT must describe a valid listener")
        if not self.allowed_hosts or "*" in self.allowed_hosts:
            raise ValueError(
                "ALLOWED_HOSTS must list explicit local host names",
            )

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return tuple(
            part.strip()
            for part in self.ALLOWED_HOSTS.split(";")
            if part.strip()
        )


def load_config() -> Config:
    return load(
        EnvSource(
            prefix="EONARQ_",
            name_style="lower_snake",
            expand_env_vars="disabled",
        ),
        schema=Config,
        cache=False,
        cache_engine=False,
        expand_env_vars="disabled",
    )
