import sys
sys.path.insert(0, '.')

# Clear module cache
for mod in list(sys.modules.keys()):
    if 'app' in mod:
        del sys.modules[mod]

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

tests = [
    ('generate a video', False, 'video'),
    ('generate a song', False, 'music'),
    ('text to speech', False, 'audio'),
    ('generate an image of a cat', False, 'vision'),
    ('write python code', True, 'code'),
    ('research with citations', False, 'text'),
    ('fast inference', False, 'text'),
    ('analyze this image', False, 'vision'),
]

print('=== Model Router Tests ===')
for task, prefer_free, expected_modality in tests:
    response = client.post('/model-router/route', json={'task': task, 'prefer_free': prefer_free})
    data = response.json()
    if 'model_id' in data:
        status = 'OK' if data['modality'] == expected_modality else 'FAIL'
        print(f'{status} {task[:30].ljust(30)} -> {data["model_id"][:30].ljust(30)} ({data["modality"]})')
    else:
        print(f'FAIL {task[:30].ljust(30)} -> ERROR: {data}')