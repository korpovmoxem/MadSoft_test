from typing import Annotated
import hashlib

import yaml
from fastapi import FastAPI, UploadFile, HTTPException, Body, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uvicorn

from app.cloud import Storage, DataBase


app = FastAPI(title='Memes API')     # Публичное API
private_app = FastAPI(title='Memes Private API')  # Приватное API
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

TAGS = [
    {
        'name': 'Мемы',
    },
]

storage = Storage()
database = DataBase()


def format_page(page: int | None) -> int:
    max_page = database.get_meme_max_page()
    if page and page > max_page:
        page = max_page
    elif page is None or page == 0:
        page = 1
    return page


@private_app.post('/auth', include_in_schema=False)
def login(credentials: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict:
    user = database.authorization(credentials.username)
    if not user:
        raise HTTPException(
            status_code=400,
            detail='Неверный логин или пароль'
        )
    with open('credentials.yaml', 'r') as file:
        hash_salt = yaml.safe_load(file)['hash_salt']
    hashed_password = hashlib.pbkdf2_hmac(
        'sha256',
        credentials.password.encode(),
        hash_salt.encode(),
        100_000).hex()
    if not database.authorization(credentials.username, hashed_password):
        raise HTTPException(
            status_code=400,
            detail='Неверный логин или пароль'
        )
    return {"access_token": credentials.username, "token_type": "bearer"}


@app.get('/memes', tags=['Мемы'], name='Получить мем')
def get_meme(meme_id: int | None = None, page: int | None = None) -> dict | object:
    """
    Получить мем по его ID или список всех мемов если не передан <code>meme_id</code>
    <h3>**Параметры**</h3>
    * **meme_id**: ID мема
    * **page**: Номер страницы коллекции мемов
    """
    page = format_page(page)
    if meme_id is None:
        return {
            'page': page,
            'max_page': database.get_meme_max_page(),
            'memes': database.get_all_memes(page),
        }
    file_info = database.get_meme_info(meme_id)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )
    return StreamingResponse(storage.get_file(f'{meme_id}.{file_info["extension"]}'), media_type=f'image/{file_info["extension"]}')


@private_app.get('/memes', tags=['Мемы'], name='Получить мем')
def get_meme(
        token: Annotated[str, Depends(oauth2_scheme)],
        meme_id: int | None = None,
        page: int | None = None
) -> dict | object:
    """
    Получить мем по его ID или список с информацией о всех мемах если не передан <code>meme_id</code>
    <h3>**Параметры**</h3>
    * **meme_id**: ID мема
    * **page**: Номер страницы коллекции мемов
    """
    page = format_page(page)
    if meme_id is None:
        return {
            'page': page,
            'max_page': database.get_meme_max_page(),
            'memes': database.get_all_memes(page, all_columns=True),
        }
    file_info = database.get_meme_info(meme_id)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )
    return StreamingResponse(storage.get_file(f'{meme_id}.{file_info["extension"]}'), media_type=f'image/{file_info["extension"]}')


@private_app.post('/memes', tags=['Мемы'], name='Добавить мем')
def add_meme(
        token: Annotated[str, Depends(oauth2_scheme)],
        text: Annotated[str, Body()],
        image: UploadFile,
) -> dict:
    """
    Загрузить новый мем в коллецкию
    <h3>**Параметры**</h3>
    * **text**: Название мема
    * **image**: Изображение мема
    """
    if 'image' not in image.content_type:
        raise HTTPException(
            status_code=422,
            detail='Неверный формат загружаемого файла. Для загрузки доступны только изображения (MIME-тип "image")',
        )
    media_content = image.content_type.split("/")
    file_id = database.add_meme(text, media_content[1], round(image.size / 1024 ** 2, 4))
    filename = f'{file_id}.{media_content[1]}'
    storage.upload_file(filename, image.file.read())
    return {
        'id': file_id,
        'name': text
    }


@private_app.put('/memes', tags=['Мемы'], name='Обновить мем')
def update_meme(
        token: Annotated[str, Depends(oauth2_scheme)],
        meme_id: Annotated[int, Body()],
        text: Annotated[str, Body()] = '',
        image: UploadFile | None = None
) -> dict:
    """
    Обновить существующий мем
    <h3>**Параметры**</h3>
    * **meme_id**: ID мема
    * **text**: Название мема
    * **image**: Изображение мема
    """
    file_info = database.get_meme_info(meme_id)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )

    if text and image:
        storage.upload_file(f'{file_info["id"]}.{file_info["extension"]}', image.file.read())
        database.update_meme_info(meme_id, text, image.content_type.split("/")[1])

    elif text:
        database.update_meme_info(meme_id, text)

    elif image:
        storage.upload_file(f'{file_info["id"]}.{file_info["extension"]}', image.file.read())
        if file_info['extension'] != image.content_type.split("/")[1]:
            database.update_meme_info(meme_id, extension=image.content_type.split("/")[1])

    return database.get_meme_info(meme_id)


@private_app.delete('/memes', tags=['Мемы'], name='Удалить мем')
def delete_meme(
        token: Annotated[str, Depends(oauth2_scheme)],
        meme_id: int
) -> dict:
    """
    Удалить существующий мем
    <h3>**Параметры**</h3>
    * **meme_id**: ID мема
    """
    file_info = database.get_meme_info(meme_id)
    if not database.get_meme_info(meme_id):
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )
    storage.delete_file(f'{file_info["id"]}.{file_info["extension"]}')
    database.update_meme_info(meme_id, delete=True)
    return database.get_meme_info(meme_id)


app.mount('/private', private_app)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
