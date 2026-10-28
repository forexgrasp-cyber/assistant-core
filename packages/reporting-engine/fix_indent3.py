with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _query_daily_facts method (lines 535-580ish) - reduce indent by 4 for method body
for i in range(534, 700):
    if i >= len(lines):
        break
    if lines[i].startswith('            ') and not lines[i].startswith('                '):
        # Lines with 12 spaces that should be 8
        lines[i] = '        ' + lines[i][12:]
    elif lines[i].startswith('                '):
        # Lines with 16 spaces that should be 12
        lines[i] = '            ' + lines[i][16:]
    elif lines[i].startswith('        ') and lines[i].strip().startswith('async def _query_'):
        # Next method - stop
        break
    elif lines[i].startswith('    async def _') or lines[i].startswith('    def _'):
        # Next method - stop
        break

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _query_daily_facts indentation')