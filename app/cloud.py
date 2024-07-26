from datetime import datetime
from math import ceil
import hashlib

from sqlalchemy import MetaData, Text, DateTime, Table, Column, create_engine, Integer, Float
import yaml
import boto3
from botocore.client import Config, UNSIGNED


class DataBase:
    """
    Подключение к БД и методы работы с ней.
    При инициализации создается подключение для многократного использования
    """

    def __init__(self):
        with open('credentials.yaml', 'r') as file:
            file_data = yaml.safe_load(file)
            credentials = file_data['mysql']
            self.__hash_salt = file_data['hash_salt']
        metadata = MetaData()
        engine = create_engine(
            f'mysql+mysqlconnector://{credentials["login"]}:{credentials["password"]}@'
            f'mysql:3306/{credentials["db"]}',
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
        self.__oauth = Table(
            'oauth',
            metadata,
            Column('name', Text),
            Column('password', Text),
        )
        metadata.create_all(engine)
        self.limit = 10

        # Создание первичного логопаса
        if not self.__get_auth():
            password = hashlib.pbkdf2_hmac(
                'sha256',
                'madsoft'.encode(),
                self.__hash_salt.encode(),
                100_000).hex()
            self.__add_auth('madsoft', password)

    def __add_auth(self, name, password):
        query = self.__oauth.insert().values(
            {
                'name': name,
                'password': hashlib.pbkdf2_hmac('sha256' ,password.encode(), self.__hash_salt.encode(), 100_000).hex()
            }
        )
        self.__connector.execute(query)
        self.__connector.commit()

    def __get_auth(self):
        query = self.__oauth.select()
        return self.__connector.execute(query).fetchall()

    def add_meme(self, filename: str, extension: str, size_mb: float) -> int:
        """
        Добавить запись в БД и возвращает ID записи
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
        Получить максимальное количество страниц в пагинации таблицы
        """
        return ceil(self.__connector.execute(self.__info.select().where(self.__info.columns.delete_date.is_(None))).rowcount / self.limit)

    def get_all_memes(self, page: int, all_columns=False) -> list[dict]:
        """
        Получить все записи таблицы info с пагинацией
        """
        query = self.__info.select().where(self.__info.columns.delete_date.is_(None))

        if all_columns:
            titles = tuple(map(lambda column: column.name, self.__info.columns))
        else:
            query = query.with_only_columns(self.__info.columns.id, self.__info.columns.filename)
            titles = ('id', 'name')

        if page == 1:
            query = query.limit(self.limit)
        else:
            query = query.limit((page + 1) * self.limit).offset(page * self.limit)

        data = self.__connector.execute(query).fetchall()
        return list(map(lambda row: dict(zip(titles, row)), data))

    def get_meme_info(self, file_id: int) -> dict | None:
        """
        Получить информацию о файле мема
        """
        query = self.__info.select().where(self.__info.columns.id == file_id and self.__info.columns.delete_date.is_(None))

        file = self.__connector.execute(query).fetchall()
        if file:
            titles = tuple(map(lambda column: column.name, self.__info.columns))
            return dict(zip(titles, file[0]))

    def update_meme_info(self, file_id: int, filename: str | None = None, extension: str | None = None, delete: bool = False) -> dict | None:
        """
        Обновить информацию о файле мема
        """
        if not delete:
            new_data = {'update_date': datetime.now()}
            if filename:
                new_data['filename'] = filename
            if extension:
                new_data['extension'] = extension
            query = self.__info.update().values(new_data).where(self.__info.columns.id == file_id)
            self.__connector.execute(query)
            self.__connector.commit()
            new_data['id'] = file_id
            return new_data

        query = self.__info.update().values({'delete_date': datetime.now()}).where(self.__info.columns.id == file_id)
        self.__connector.execute(query)
        self.__connector.commit()

    def authorization(self, name: str | None = None, password: str | None = None):
        if not password:
            query = self.__oauth.select().where(self.__oauth.columns.name == name)
            return self.__connector.execute(query).fetchall()
        if name and password:
            query = self.__oauth.select().where(self.__oauth.columns.name == name and self.__oauth.columns.password == password)
            return self.__connector.execute(query).fetchall()


class Storage:
    """
    Инициализация подключения к объектному хранилищу и методы работы с ним.
    При инициализации создается подключение для многократного использования
    """

    def __init__(self):
        with open('credentials.yaml') as file:
            credentials = yaml.safe_load(file)['storage']
        session = boto3.session.Session()
        self.__bucket = credentials['bucket']
        self.__client = session.client(
            service_name='s3',
            config=Config(signature_version=UNSIGNED),
            endpoint_url=credentials['endpoint_url'],
        )

    def upload_file(self, filename, file: bytes):
        """
        Загрузка файла в объектное хранилище
        :param filename: Имя файла (ID записи БД), с которым он будет загружен в хранилище.
        :param file: Байтовая строка с содержимым файла
        """
        self.__client.put_object(Bucket=self.__bucket, Key=filename, Body=file)

    def get_file(self, filename):
        """
        Получить файл иp объектного хранилища по его имени
        :param filename: Имя файла с расширением (picture.png)
        :return: Экземпляр класса StreamingResponse с содержимым файла
        """
        file = self.__client.get_object(Bucket=self.__bucket, Key=filename)
        return file['Body']

    def delete_file(self, filename):
        """
        Удалить файл из объектного хранилища
        :param filename: Имя файла с расширением (picture.png)
        """
        self.__client.delete_object(Bucket=self.__bucket, Key=filename)

