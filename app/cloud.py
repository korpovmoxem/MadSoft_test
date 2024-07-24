from datetime import datetime
from math import ceil

from sqlalchemy import MetaData, Text, DateTime, Table, Column, create_engine, Integer, Float
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
            Column('extension', Text),
            Column('size_mb', Float),
            Column('create_date', DateTime),
            Column('update_date', DateTime),
            Column('delete_date', DateTime),
        )
        metadata.create_all(engine)
        self.limit = 10

    def add_meme(self, filename: str, extension: str, size_mb: float) -> int:
        """
        Добавляет запись в БД и возвращает ID записи
        """
        query = self.__info.insert().values(
            {
                'filename': filename,
                'extension': extension,
                'size_mb': size_mb,
                'create_date': datetime.now()
            }
        )
        query_executing = self.__connector.execute(query)
        self.__connector.commit()
        return query_executing.inserted_primary_key[0]

    def get_meme_max_page(self) -> int:
        """
        Возвращает максимальное количество страниц в пагинации таблицы
        """
        return ceil(self.__connector.execute(self.__info.select()).rowcount / self.limit)

    def get_all_memes(self, page: int, all_columns=False) -> list[dict]:
        """
        Возвращает все записи таблицы info с пагинацией
        """
        query = self.__info.select()

        if all_columns:
            query = query.with_only_columns(self.__info.columns.id, self.__info.columns.filename)
            titles = tuple(map(lambda column: column.name, self.__info.columns))
        else:
            titles = ('id', 'name')

        if page == 1:
            query = query.limit(self.limit)
        else:
            query = query.limit((page + 1) * self.limit).offset(page * self.limit)

        data = self.__connector.execute(query).fetchall()
        return list(map(lambda row: dict(zip(titles, row)), data))

    def get_extension(self, file_id: int) -> str:
        """
        Возвращает расширение файла
        """
        query = (
            self.__info.select().
            with_only_columns(self.__info.columns.extension).
            where(self.__info.columns.id == file_id)
        )
        file = self.__connector.execute(query).fetchall()[0]
        return file[0]



class Storage:
    """
    Инициализация подключения к объектному хранилищу и методы работы с ним.
    При инициализации создает подключение для многократного использования
    """

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

    def upload_file(self, filename, file: bytes):
        """
        :param filename: Имя файла (ID записи БД), с которым он будет загружен в хранилище.
        :param file: Байтовая строка с содержимым файла
        """
        self.__client.put_object(Bucket=self.__bucket, Key=filename, Body=file)

    def get_all_files(self):
        storage_keys = self.__client.list_objects(Bucket=self.__bucket)
        if 'Contents' not in storage_keys:
            return
        return self.__client.list_objects(Bucket=self.__bucket)['Contents']

    def get_file(self, filename):
        file = self.__client.get_object(Bucket=self.__bucket, Key=filename)
        return file['Body']

