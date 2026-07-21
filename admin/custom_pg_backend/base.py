import socket as _socket
import ssl as _ssl
import logging

logger = logging.getLogger("custom_pg_backend")

_db_host = None
_pooler_ip = None


def patch_socket_getaddrinfo():
    global _db_host, _pooler_ip
    import os as _os
    _db_host = _os.getenv("DB_HOST", "")
    _pooler_host = _os.getenv("POOLER_HOST", "aws-0-us-east-1.pooler.supabase.com")
    if not _db_host:
        return

    try:
        _infos = _socket.getaddrinfo(_pooler_host, 6543, _socket.AF_INET, _socket.SOCK_STREAM)
        if _infos:
            _pooler_ip = _infos[0][4][0]
        else:
            return
    except Exception:
        return

    _original_getaddrinfo = _socket.getaddrinfo

    def _patched_getaddrinfo(host, port, *args, **kwargs):
        if host and _db_host and host.lower() == _db_host.lower():
            result = _original_getaddrinfo(_pooler_ip, port, *args, **kwargs)
            return result
        return _original_getaddrinfo(host, port, *args, **kwargs)

    _socket.getaddrinfo = _patched_getaddrinfo
    logger.info("Patched socket.getaddrinfo: %s -> %s", _db_host, _pooler_ip)


from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.postgresql.operations import DatabaseOperations
from django.db.backends.postgresql.features import DatabaseFeatures
from django.db.backends.postgresql.client import DatabaseClient
from django.db.backends.postgresql.introspection import DatabaseIntrospection
from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = "postgresql"
    display_name = "PostgreSQL"
    Database = None

    data_types = DatabaseFeatures.data_types if hasattr(DatabaseFeatures, 'data_types') else {}

    operators = {
        "exact": "= %s",
        "iexact": "= UPPER(%s)",
        "contains": "LIKE %s",
        "icontains": "LIKE UPPER(%s)",
        "regex": "~ %s",
        "iregex": "~* %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s",
        "endswith": "LIKE %s",
        "istartswith": "LIKE UPPER(%s)",
        "iendswith": "LIKE UPPER(%s)",
    }

    data_types = {
        "AutoField": "integer",
        "BigAutoField": "bigint",
        "BinaryField": "bytea",
        "BooleanField": "boolean",
        "CharField": "varchar(%(max_length)s)",
        "DateField": "date",
        "DateTimeField": "timestamp with time zone",
        "DecimalField": "numeric(%(max_digits)s, %(decimal_places)s)",
        "DurationField": "interval",
        "FileField": "varchar(%(max_length)s)",
        "FilePathField": "varchar(%(max_length)s)",
        "FloatField": "double precision",
        "IntegerField": "integer",
        "BigIntegerField": "bigint",
        "IPAddressField": "inet",
        "GenericIPAddressField": "inet",
        "JSONField": "jsonb",
        "OneToOneField": "integer",
        "PositiveBigIntegerField": "bigint",
        "PositiveIntegerField": "integer",
        "PositiveSmallIntegerField": "smallint",
        "SlugField": "varchar(%(max_length)s)",
        "SmallAutoField": "smallint",
        "SmallIntegerField": "smallint",
        "TextField": "text",
        "TimeField": "time",
        "UUIDField": "uuid",
    }

    data_type_check_constraints = {
        "PositiveBigIntegerField": '"%(column)s" >= 0',
        "PositiveIntegerField": '"%(column)s" >= 0',
        "PositiveSmallIntegerField": '"%(column)s" >= 0',
    }

    SchemaEditorClass = DatabaseSchemaEditor
    creation_class = None

    def __init__(self, settings_dict, alias=None):
        import pg8000
        self.Database = pg8000
        super().__init__(settings_dict, alias)

    def get_connection_params(self):
        settings_dict = self.settings_dict
        conn_params = {}
        if settings_dict["NAME"]:
            conn_params["database"] = settings_dict["NAME"]
        if settings_dict["USER"]:
            conn_params["user"] = settings_dict["USER"]
        if settings_dict["PASSWORD"]:
            conn_params["password"] = settings_dict["PASSWORD"]
        if settings_dict["HOST"]:
            conn_params["host"] = settings_dict["HOST"]
        if settings_dict["PORT"]:
            conn_params["port"] = int(settings_dict["PORT"])
        conn_params["timeout"] = settings_dict.get("OPTIONS", {}).get("connect_timeout", 10)
        return conn_params

    def get_new_connection(self, conn_params):
        import pg8000
        host = conn_params.get("host", "")
        is_vercel = __import__("os").getenv("VERCEL", "0") == "1"

        ssl_context = None
        if is_vercel and host and "supabase.co" in host:
            ssl_context = _ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = _ssl.CERT_REQUIRED

        kwargs = {}
        for k in ("database", "user", "password", "host", "port", "timeout"):
            if k in conn_params:
                kwargs[k] = conn_params[k]

        kwargs["ssl_context"] = ssl_context
        kwargs["ssl"] = True

        conn = pg8000.connect(**kwargs)
        return conn

    def ensure_connection(self):
        self.validate_thread_sharing()
        if self.connection is None:
            wrap_database_errors(
                lambda: self.connect()
            )

    def connect(self):
        if self.connection is not None:
            return
        self.connect_params = self.get_connection_params()
        self.connection = self.get_new_connection(self.connect_params)
        self.connection.autocommit = True

    def create_cursor(self, name=None):
        cursor = self.connection.cursor()
        return cursor

    def _set_autocommit(self, autocommit):
        self.connection.autocommit = autocommit

    def is_usable(self):
        try:
            self.connection.run("SELECT 1")
            return True
        except Exception:
            return False

    def _close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def chunked_cursor(self):
        return self._cursor()

    def _cursor(self):
        self.ensure_connection()
        return self.create_cursor()

    def _commit(self):
        if self.connection is not None:
            try:
                self.connection.commit()
            except Exception:
                pass

    def _rollback(self):
        if self.connection is not None:
            try:
                self.connection.rollback()
            except Exception:
                pass


def wrap_database_errors(func):
    try:
        return func()
    except Exception as e:
        from django.db.utils import DatabaseError
        raise DatabaseError(str(e)) from e
