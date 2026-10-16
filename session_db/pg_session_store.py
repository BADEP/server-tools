# Copyright (c) Odoo SA 2017
# @author Nicolas Seinlet
# Copyright (c) ACSONE SA 2022
# @author Stéphane Bidoul
import contextlib
import functools
import json
import logging
import os
import sys

import psycopg2

import odoo
from odoo.http import session as http_session

_logger = logging.getLogger(__name__)

lock = None
if odoo.evented:
    import gevent.lock

    lock = gevent.lock.RLock()
elif odoo.tools.config["workers"] == 0:
    import threading

    lock = threading.RLock()


def with_lock(func):
    def wrapper(*args, **kwargs):
        try:
            if lock is not None:
                lock.acquire()
            return func(*args, **kwargs)
        finally:
            if lock is not None:
                lock.release()

    return wrapper


def with_cursor(func):
    def wrapper(self, *args, **kwargs):
        tries = 0
        while True:
            tries += 1
            try:
                self._ensure_connection()
                return func(self, *args, **kwargs)
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                self._close_connection()
                if tries > 4:
                    _logger.warning(
                        "session_db operation try %s/5 failed, aborting", tries
                    )
                    raise
                _logger.info("session_db operation try %s/5 failed, retrying", tries)

    return wrapper


class PGSessionStore(http_session.SessionStore):
    def __init__(self, uri, session_cls=http_session.Session):
        super().__init__(session_cls=session_cls)
        self._uri = uri
        self._cr = None
        self._open_connection()
        self._setup_db()

    def __del__(self):
        self._close_connection()

    @with_lock
    def _ensure_connection(self):
        if self._cr is None:
            self._open_connection()

    @with_lock
    def _open_connection(self):
        self._close_connection()
        cnx = odoo.sql_db.db_connect(self._uri, allow_uri=True)
        self._cr = cnx.cursor()
        self._cr._cnx.autocommit = True

    @with_lock
    def _close_connection(self):
        """Return cursor to the pool."""
        if self._cr is not None:
            with contextlib.suppress(psycopg2.Error):
                self._cr.close()
            self._cr = None

    @with_lock
    @with_cursor
    def _setup_db(self):
        self._cr.execute(
            """
                CREATE TABLE IF NOT EXISTS http_sessions (
                    sid varchar PRIMARY KEY,
                    write_date timestamp without time zone NOT NULL,
                    payload text NOT NULL
                )
            """
        )

    @with_lock
    @with_cursor
    def save(self, session):
        payload = json.dumps(dict(session))
        self._cr.execute(
            """
                INSERT INTO http_sessions(sid, write_date, payload)
                    VALUES (%(sid)s, now() at time zone 'UTC', %(payload)s)
                ON CONFLICT (sid)
                DO UPDATE SET payload = %(payload)s,
                              write_date = now() at time zone 'UTC'
            """,
            {"sid": session.sid, "payload": payload},
        )

    @with_lock
    @with_cursor
    def delete(self, session):
        self._cr.execute("DELETE FROM http_sessions WHERE sid=%s", (session.sid,))

    @with_lock
    @with_cursor
    def get(self, sid, *, keep_sid=False):
        self._cr.execute("SELECT payload FROM http_sessions WHERE sid=%s", (sid,))
        row = self._cr.fetchone()
        if row is None:
            if keep_sid:
                return self.session_cls({}, sid, new=False)
            return self.new()
        try:
            data = json.loads(row[0])
        except ValueError:
            _logger.debug("Could not load session data. Use empty session.")
            data = {}
        return self.session_cls(data, sid, new=False)

    # rotate, generate_key, is_valid_session_id and delete_old_sessions are
    # independent of the actual storage backend and inherited from Odoo's
    # SessionStore.

    @with_lock
    @with_cursor
    def vacuum(self, max_lifetime=http_session.SESSION_LIFETIME):
        self._cr.execute(
            "DELETE FROM http_sessions "
            "WHERE now() at time zone 'UTC' - write_date > %s",
            (f"{max_lifetime} seconds",),
        )

    @with_lock
    @with_cursor
    def get_missing_session_identifiers(self, identifiers: list[str]) -> set[str]:
        """
        :param identifiers: session identifiers whose file existence must be checked
                            identifiers are a part session sid (first 42 chars)
        :type identifiers: iterable
        :return: the identifiers which are not present on the filesystem
        :rtype: set

        Note 1:
        Working with identifiers 42 characters long means that
        we don't have to work with the entire sid session,
        while maintaining sufficient entropy to avoid collisions.
        See details in ``generate_key``.

        Note 2:
        Scans the session store for inactive (GC'd) sessions.
        Performance is acceptable for an infrequent background job.
        """
        missing_identifiers = set()
        for identifier in identifiers:
            self._cr.execute(
                "SELECT sid FROM http_sessions WHERE sid LIKE %s||'%%' LIMIT 1",
                (identifier,),
            )
            if self._cr.rowcount == 0:
                missing_identifiers.add(identifier)
        return missing_identifiers

    @with_lock
    @with_cursor
    def delete_from_identifiers(self, identifiers: list[str]) -> None:
        for identifier in identifiers:
            if not http_session._session_identifier_re.match(identifier):
                raise ValueError(
                    "Identifier format incorrect, "
                    "did you pass in a string instead of a list?"
                )
            self._cr.execute(
                "DELETE FROM http_sessions WHERE sid LIKE %s||'%%'", (identifier,)
            )


_original_session_store = http_session.session_store


@functools.cache
def session_store():
    session_db_uri = os.environ.get("SESSION_DB_URI")
    if session_db_uri:
        _logger.debug("HTTP sessions stored in: db")
        return PGSessionStore(session_db_uri, session_cls=http_session.Session)
    return _original_session_store()


# Monkey patch of standard function: odoo.http.session.session_store is imported
# by name in several modules, replace it wherever it has already been imported.
_logger.debug("Monkey patching session store")
for _module in list(sys.modules.values()):
    if vars(_module).get("session_store") is _original_session_store:
        _module.session_store = session_store
