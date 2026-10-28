with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _execute_data_source method - elif statements should be at indent 12
for i in range(498, 520):  # 0-indexed: lines 499-520
    if lines[i].strip().startswith('elif ') or lines[i].strip().startswith('else:'):
        lines[i] = '            ' + lines[i].lstrip()

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed elif indentation')