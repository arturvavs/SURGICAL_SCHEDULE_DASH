import os
import pandas as pd
from dotenv import load_dotenv, dotenv_values
from sqlalchemy import create_engine
from sql_p import sql
import oracledb as odb

load_dotenv()
host = os.environ.get("HOST_DB")
port = os.environ.get('PORT_DB')
service_name = os.environ.get("SERVICE_NAME_DB")
user = os.environ.get("USER_DB")
password = os.environ.get("PASSWORD_DB")
engine = create_engine(f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service_name}")


def get_data(query, data_selecionada=None):
    try:
        with engine.connect() as connection:
            data = pd.read_sql(query, connection, params={'dt_inicio': data_selecionada})
            return data
    except odb.Error as e:
        print(f'Error: {e}')
        return pd.DataFrame()

#data = get_data(sql,'2025-02-27')
#print(data)