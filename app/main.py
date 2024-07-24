from fastapi import FastAPI, UploadFile, HTTPException
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
def get_meme(meme_id: str | None = None, page: int | None = None) -> dict | object:
    page = format_page(page)
    if meme_id is None:
        return {
            'page': page,
            'max_page': database.get_meme_max_page(),
            'memes': database.get_all_memes(page),
        }
    return


@private_app.get('/memes')
def get_meme(meme_id: int | None = None, page: int | None = None) -> dict | object:
    page = format_page(page)
    if meme_id is None:
        return {
            'page': page,
            'max_page': database.get_meme_max_page(),
            'memes': database.get_all_memes(page, all_columns=True),
        }
    extension = database.get_extension(meme_id)
    return StreamingResponse(storage.get_file(f'{meme_id}.{extension}'), media_type=f'image/{extension}')


@private_app.post('/memes')
def add_meme(picture: UploadFile, text: str):
    if 'image' not in picture.content_type:
        raise HTTPException(
            status_code=422,
            detail='Неверный формат загружаемого файла. Для загрузки доступны только изображения (MIME-тип "image")',
        )
    media_content = picture.content_type.split("/")
    file_id = database.add_meme(text, media_content[1], round(picture.size / 1024 ** 2, 2))
    filename = f'{file_id}.{media_content[1]}'
    storage.upload_file(filename, picture.file.read())


app.mount('/private', private_app)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
