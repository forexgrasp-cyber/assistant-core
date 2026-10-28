with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'async def _execute_data_source')
if idx >= 0:
    # Check for any non-whitespace characters in the indentation area
    for i in range(idx-100, idx+200):
        if i < 0 or idx+i >= len(content):
            continue
        b = content[i:i+1]
        if b in (b' ', b'	', b'
', b''):
            continue
        # Found non-whitespace in indentation area
        if i < idx:
            print(f'Before def: offset {idx+i} = {content[idx+i-10:idx+i+10]!r}')
            break

print('Done checking')
