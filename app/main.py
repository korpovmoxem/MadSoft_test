from fastapi import FastAPI, UploadFile, HTTPException
import uvicorn


app = FastAPI()     # Публичное API
private_app = FastAPI()  # Приватное API

ALLOWED_FILE_FORMATS = ['image/jpeg', 'image/png']


@app.get('/memes')
def get_meme(meme_id: str | None = None) -> dict | list:
    if meme_id is not None:
        pass
    return


@private_app.get('/memes')
def get_meme(meme_id: str | None = None) -> dict | list:
    if meme_id is not None:
        pass
    return


@private_app.post('/memes')
def add_meme(picture: UploadFile, text: str):
    if picture.content_type not in ALLOWED_FILE_FORMATS:
        raise HTTPException(
            status_code=422,
            detail='Неверный формат загружаемого файла. Поддерживаемые форматы: jpeg, png',
        )

    return text


app.mount('/private', private_app)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
