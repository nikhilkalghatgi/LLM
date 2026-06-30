"""FastAPI routers for the production endpoints.

Each router is a self-contained feature surface mounted onto the main app in
``serve/api.py``:

* ``auth``      -- login / whoami
* ``documents`` -- data-pipeline metadata listing
* ``jobs``      -- async submit + poll + SSE stream
* ``review``    -- human-in-the-loop queue
* ``metrics``   -- dashboard data + audit retrieval
"""
