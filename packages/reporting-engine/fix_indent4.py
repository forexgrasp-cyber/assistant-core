with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _query_daily_facts method - fix for loop body
for i in range(546, 600):
    if i >= len(lines):
        break
    if lines[i].startswith('        for ') or lines[i].startswith('        if ') or lines[i].startswith('        elif ') or lines[i].startswith('        else:'):
        # These should be at 8 spaces (inside method), their bodies at 12
        pass
    elif lines[i].startswith('        ') and not lines[i].startswith('            '):
        # Line at 8 spaces that should be 12 (inside for/if)
        stripped = lines[i].lstrip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith('return'):
            lines[i] = '            ' + stripped
    elif lines[i].startswith('    async def _') or lines[i].startswith('    def _'):
        # Next method - stop
        break

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _query_daily_facts for loop body')