"""
core/__init__.py
================
WHAT THIS FILE DOES
-------------------
Marks `app/core/` as a package. It holds no logic of its own.

WHAT LIVES IN THIS PACKAGE
--------------------------
The three pieces of plumbing that everything else is built on:

    config.py      every setting, read once from the environment
    security.py    password hashing and JWT creation/decoding
    celery_app.py  the Celery application the background worker runs

They have nothing in common with each other. What they share is a position:
every other layer needs them, and they need nothing from any other layer. That
is what makes them safe to import from anywhere -- an import of `core` can
never create a cycle, because it never points back up.

WHY IT IS DELIBERATELY EMPTY
----------------------------
Re-exporting the contents here (`from app.core import settings`) would be
convenient by a few characters and would cost something real: importing *any*
core module would then drag in *all* of them, so a script that only wanted a
setting would also construct the Celery app and import passlib.

Importing straight from the module that owns the thing keeps that honest:

        from app.core.config import settings
        from app.core.security import create_access_token
"""
