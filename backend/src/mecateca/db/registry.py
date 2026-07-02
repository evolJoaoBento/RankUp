"""Import all ORM models so Base.metadata is fully populated (create_all / Alembic)."""

from mecateca.contexts.assessment import models as _assessment  # noqa: F401
from mecateca.contexts.catalog import models as _catalog  # noqa: F401
from mecateca.contexts.duels import models as _duels  # noqa: F401
from mecateca.contexts.identity import models as _identity  # noqa: F401
from mecateca.contexts.metering import models as _metering  # noqa: F401
from mecateca.contexts.progression import models as _progression  # noqa: F401
from mecateca.contexts.social import models as _social  # noqa: F401
from mecateca.contexts.tutoring import models as _tutoring  # noqa: F401
