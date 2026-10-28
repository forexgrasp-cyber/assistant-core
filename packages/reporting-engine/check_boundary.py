with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

idx = content.find(b'return "|".join(key_parts)')
if idx >= 0:
    # Show 200 bytes after
    print(repr(content[idx:idx+300]))