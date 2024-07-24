from typing import Annotated

from fastapi import FastAPI, UploadFile, HTTPException, Body
from fastapi.responses import StreamingResponse
import uvicorn

from cloud import Storage, DataBase


app = FastAPI()     # Публичное API
private_app = FastAPI()  # Приватное API

storage = Storage()
database = DataBase()


def format_page(page: int | None) -> int:
    max_page = database.get_meme_max_page()
    if page and page > max_page:
        page = max_page
    elif page is None or page == 0:
        page = 1
    return page

@app.get('/memes')
def get_meme(meme_id: int | None = None, page: int | None = None) -> dict | object:
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


@private_app.get('/memes')
def get_meme(meme_id: int | None = None, page: int | None = None) -> dict | object:
    page = format_page(page)
    if meme_id is None:
        return {
            'page': page,
            'max_page': database.get_meme_max_page(),
            'memes': database.get_all_memes(page, all_columns=True),
        }
    file_info = database.get_meme_info(meme_id)
    return StreamingResponse(storage.get_file(f'{meme_id}.{file_info["extension"]}'), media_type=f'image/{file_info["extension"]}')


@private_app.post('/memes')
def add_meme(picture: UploadFile, text: Annotated[str, Body()]) -> dict:
    if 'image' not in picture.content_type:
        raise HTTPException(
            status_code=422,
            detail='Неверный формат загружаемого файла. Для загрузки доступны только изображения (MIME-тип "image")',
        )
    media_content = picture.content_type.split("/")
    file_id = database.add_meme(text, media_content[1], round(picture.size / 1024 ** 2, 2))
    filename = f'{file_id}.{media_content[1]}'
    storage.upload_file(filename, picture.file.read())
    return {
        'id': file_id,
        'name': text
    }


@private_app.put('/memes')
def update_meme(meme_id: Annotated[int, Body()], text: Annotated[str, Body()] = '', picture: UploadFile | None = None) -> dict:
    file_info = database.get_meme_info(meme_id)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )

    if text and picture:
        storage.upload_file(f'{file_info["id"]}.{file_info["extension"]}', picture.file.read())
        database.update_file_info(meme_id, text, picture.content_type.split("/")[1])

    elif text:
        database.update_file_info(meme_id, text)

    elif picture:
        storage.upload_file(f'{file_info["id"]}.{file_info["extension"]}', picture.file.read())
        if file_info['extension'] != picture.content_type.split("/")[1]:
            database.update_file_info(meme_id, extension=picture.content_type.split("/")[1])

    return database.get_meme_info(meme_id)


@private_app.delete('/memes')
def delete_meme(meme_id: int) -> dict:
    file_info = database.get_meme_info(meme_id)
    if not database.get_meme_info(meme_id):
        raise HTTPException(
            status_code=404,
            detail=f'Мем с ID {meme_id} не найден',
        )
    storage.delete_file(f'{file_info["id"]}.{file_info["extension"]}')
    database.update_file_info(meme_id, delete=True)
    return database.get_meme_info(meme_id)




app.mount('/private', private_app)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
