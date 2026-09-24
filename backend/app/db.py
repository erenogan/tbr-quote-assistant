from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from app.config import settings

pool = ConnectionPool(
    settings.database_url,
    kwargs={"row_factory": dict_row, "options": "-c search_path=case_seed"},
    open=True,
)

#pool ekledim çünkü her seferined istek tutmak yerine havuzda bir kaç tane bağlantıyı baştan açık tutacağım
