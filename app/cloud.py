from datetime import datetime

from sqlalchemy import MetaData, Text, DateTime, Table, Column, Boolean, create_engine, Integer, Float
import yaml
import boto3


class DataBase:
    """
    Подключение к БД и методы работы с ней.
    При инициализации создает подключение для многократного использования
    """

    def __init__(self):
        with open('credentials.yaml', 'r') as file:
            credentials = yaml.safe_load(file)['mysql']
        metadata = MetaData()

        engine = create_engine(
            f'mysql+mysqlconnector://{credentials["login"]}:{credentials["password"]}@{credentials["host"]}:{credentials["port"]}/{credentials["db"]}',
            connect_args={'ssl_ca': 'CA.pem'},
        )
        self.__connector = engine.connect()
        self.__info = Table(
            'info',
            metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('filename', Text),
            Column('filename_extension', Text),
            Column('text', Text),
            Column('size_mb', Float),
            Column('create_date', DateTime),
            Column('update_date', DateTime),
            Column('delete_date', DateTime),
        )
        metadata.create_all(engine)

    def add_meme(self, filename: str, text: str, size_mb: float):
        pass

    def get_all_memes_private(self) -> list[dict]:
        """
        Возвращает все записи таблицы info
        """
        query = self.__info.select()
        data = self.__connector.execute(query).fetchall()
        titles = tuple(map(lambda column: column.name, self.__info.columns))
        return list(map(lambda row: dict(zip(titles, row)), data))


class Storage:

    def __init__(self):
        with open('credentials.yaml') as file:
            credentials = yaml.safe_load(file)['storage']
        session = boto3.session.Session()
        self.__bucket = credentials['bucket']
        self.__client = session.client(
            service_name='s3',
            aws_access_key_id=credentials['access_key'],
            aws_secret_access_key=credentials['secret_key'],
            endpoint_url='https://storage.yandexcloud.net'
        )

    def upload_file(self, filename, file):
        return self.__client.put_object(Bucket=self.__bucket, Key=filename, Body=file)

    def get_all_files(self):
        storage_keys = self.__client.list_objects(Bucket=self.__bucket)
        if 'Contents' not in storage_keys:
            return
        return self.__client.list_objects(Bucket=self.__bucket)['Contents']

    def get_file(self, filename):
        file = self.__client.get_object(Bucket=self.__bucket,Key=filename)
        return file['Body']


DataBase().get_all_memes_private()
