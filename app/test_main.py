import os

from fastapi.testclient import TestClient

from .main import app, private_app

client = TestClient(private_app)


def test_auth() -> dict:
    response = client.post(
        '/auth',
        data={
            'username': 'madsoft',
            'password': 'madsoft',
        },
    )
    assert response.status_code == 200
    assert response.json() is not None
    return response.json()


def test_post_meme():
    auth = test_auth()
    images_dir = 'test_images'
    images = os.listdir('test_images')
    for index, filename in enumerate(images):
        file_extension = filename.split('.')[-1]
        with open(f'{images_dir}{os.sep}{filename}', 'rb') as file:
            response = client.post(
                '/memes',
                headers={"Authorization": f"Bearer {auth['access_token']}"},
                data={
                    'text': f'test_meme_{index}',
                },
                files={'image': (filename, file)}
            )
        if 'txt' in file_extension:
            assert response.status_code == 422
        else:
            assert response.status_code == 200


def test_get_meme():
    auth = test_auth()
    response = client.get('/memes', headers={"Authorization": f"Bearer {auth['access_token']}"})
    assert response.status_code == 200
    for i in response.json()['memes']:
        response = client.get(f'/memes?meme_id={int(i["id"])}', headers={"Authorization": f"Bearer {auth['access_token']}"})
        assert response.status_code == 200
    response = client.get(f'/memes?meme_id={int(len(response.json()["memes"]) + 1)}', headers={"Authorization": f"Bearer {auth['access_token']}"})
    assert response.status_code == 404


def test_put_meme():
    pass