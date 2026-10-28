with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'async def _execute_data_source')
if idx >= 0:
    # Check 100 bytes before and after
    start = max(0, idx - 100)
    end = idx + 200
    snippet = content[idx-100:idx+200]
    # Check each byte
    for i in range(-50, 200):
        pos = idx + i
        if 0 <= idx + i < len(content):
            b = content[idx+i:idx+i+1]
            if b not in (b' ', b'\t', b'\n', b'\r'):
                if b >= 128:
                    print(f'Non-ASCII at offset {idx+i}: {content[idx+i:idx+i+1]!r} (ord={content[idx+i:idx+i+1][0]})')
                else:
                    print(f'Offset {idx+i}: {content[idx+i:idx+i+1]!r} (ord={content[idx+i:idx+i+1][0]})')

print('Done')