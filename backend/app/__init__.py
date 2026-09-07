"""
app/__init__.py
===============
WHAT THIS FILE DOES
-------------------
Marks `app/` as a Python package. That is genuinely all it does.

WHY AN EMPTY FILE IS STILL NECESSARY
------------------------------------
Its presence is what lets every import in the project be written as a path
through this package:

        from app.core.config import settings
        from app.models import Document

and it is why the server is started as `uvicorn app.main:app` -- the first
`app` there is this package, and the second is the FastAPI object defined
inside `main.py`.

WHY IT IS DELIBERATELY EMPTY
----------------------------
Two other package markers in this project do real work. `models/__init__.py`
imports every model so SQLAlchemy's registry is complete, and
`tasks/__init__.py` imports every Celery task so the worker can register them.
Both are load-bearing, and both explain themselves.

This one is not, and should stay that way. Anything placed here runs on *every*
import of *anything* under `app.` -- including Alembic, the Celery worker, and
any one-off script -- so a stray import or side effect here is paid for
everywhere and is awkward to trace back to its source. The interesting wiring
belongs in `main.py`, which is imported only when the API actually starts.
"""
