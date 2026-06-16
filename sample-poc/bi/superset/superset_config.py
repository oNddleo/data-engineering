# Superset runtime config. Picked up automatically because the image puts
# /app/pythonpath on PYTHONPATH and Superset imports `superset_config` from there.
#
# WHY THIS FILE EXISTS: the stock image does NOT read SQLALCHEMY_DATABASE_URI from
# the environment — without this, both the init and the webserver containers fall
# back to a local, ephemeral SQLite. The admin user created by the init container
# then lives in a throwaway DB the webserver never sees ("Invalid login"). Reading
# the shared Postgres URI here makes init + webserver use the same metadata DB.
import os

SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
