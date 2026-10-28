with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'return "|".join(key_parts)')
if idx >= 0:
    # Check for any non-whitespace in the boundary area
    for i in range(idx - 50, idx + 200):
        if i < len(content):
            b = content[i:i+1]
            if b not in (b' ', b'\t', b'\n', b'\r'):
                print(f'Offset {idx+i}: {content[idx+i:idx+i+10]!r} is not whitespace')
print('Done')