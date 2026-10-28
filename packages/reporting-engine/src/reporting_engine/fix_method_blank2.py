with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'rb') as f:
    content = f.read()

old_text = '''        return "|".join(key_parts)\n\n    async def _execute_data_source('''

new_text = '''        return "|".join(key_parts)\n\n    async def _execute_data_source('''

content = content.replace(old_text, new_text)

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'wb') as f:
    f.write(content)

print('Fixed')