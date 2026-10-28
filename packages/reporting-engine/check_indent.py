with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'async def _execute_data_source')
if idx >= 0:
    # Check for any non-space/tab/newline characters in the indentation
    start = max(0, idx - 100)
    end = idx + 200
    snippet = content[idx-100:idx+200]
    print('Snippet around _execute_data_source:')
    print(repr(content[idx-50:idx+200]))
    print('---')
    # Check each byte
    for i, b in enumerate(content[idx-50:idx+200]):
        if content[idx+i] in (9, 32, 10, 13):
            continue
        if idx + i < len(content):
            print(f'Offset {idx+i}: {content[idx+i:idx+i+1]!r}')