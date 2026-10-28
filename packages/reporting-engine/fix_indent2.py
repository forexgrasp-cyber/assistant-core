with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 520 (0-indexed: 519)
lines[519] = '                raise ValueError(f"Unknown data source type: {source.type}")\n'
# Fix line 521 (blank)
lines[520] = '\n'
# Fix line 524
lines[523] = '            return QueryResult(\n'
# Fix lines 525-531 (QueryResult fields)
for i in range(524, 531):
    if lines[i].startswith('            '):
        lines[i] = '            ' + lines[i][12:]

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed')