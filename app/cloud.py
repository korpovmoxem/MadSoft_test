from datetime import datetime

from sqlalchemy import MetaData, Text, DateTime, Table, Column, Boolean, create_engine, Integer, Float
import yaml
from requests import request


class DataBase:

    def __init__(self):
        with open('credentials.yaml', 'r') as file:
            credentials = yaml.safe_load(file)['mysql']
        metadata = MetaData()

        engine = create_engine(
            f'mysql+mysqlconnector://{credentials["login"]}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{credentials["db"]}',
            connect_args={'ssl_ca': 'CA.pem'},
            echo=True)
        self.__connector = engine.connect()
        self.__info = Table(
            'info',
            metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('filename', Text),
            Column('text', Text),
            Column('size_mb', Float),
            Column('create_date', DateTime),
            Column('update_date', DateTime),
            Column('delete_date', DateTime),
        )
        metadata.create_all(engine)

    def add_meme(self, filename: str, text: str, size_mb: float):
        pass


class Storage:

    def __init__(self):
        with open('credentials.yaml') as file:
            credentials = yaml.safe_load(file)['storage']
        self.request_url = f'http://storage.yandexcloud.net/{credentials["bucket"]}/{credentials["key"]}'


    def add_meme(self, file):
        method = 'upload'
        re = request('put', f'{self.request_url}/{method}')
        print(re.text)


Storage().add_meme(1)