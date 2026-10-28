with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'return "|".join(key_parts)')
if idx >= 0:
    idx2 = content.find(b'async def _execute_data_source', idx)
    if idx2 >= 0:
        between = content[idx:idx2]
        print('Between return and method:', repr(between))
