from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

from cloud import Storage, DataBase


app = FastAPI()     # Публичное API
private_app = FastAPI()  # Приватное API

storage = Storage()
database = DataBase()

@app.get('/memes')
def get_meme(meme_id: str | None = None) -> dict | list:
    if meme_id is not None:
        pass
    return


@private_app.get('/memes')
def get_meme(meme_id: str | None = None):
    if meme_id is not None:
        pass
    return StreamingResponse(storage.get_file(meme_id), media_type='image/jpeg')


@private_app.post('/memes')
def add_meme(picture: UploadFile, text: str):
    if 'image' not in picture.content_type:
        raise HTTPException(
            status_code=422,
            detail='Неверный формат загружаемого файла. Для загрузки доступны только изображения (MIME-тип "image")',
        )
    filename = f'{text}.{picture.content_type.split("/")[1]}'
    storage.upload_file(filename, picture.file.read())



app.mount('/private', private_app)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
