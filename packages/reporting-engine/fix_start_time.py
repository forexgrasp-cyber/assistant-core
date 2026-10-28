with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add start_time definition at the start of the try block in _execute_data_source
# Line 496 (0-indexed: 495) is '        try:\n'
# Insert after it
lines.insert(496, '            start_time = datetime.utcnow()\n')

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Added start_time definition')