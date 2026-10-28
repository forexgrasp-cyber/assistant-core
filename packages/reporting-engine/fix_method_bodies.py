with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix method bodies throughout - reduce 12->8, 16->12, etc.
for i in range(len(lines)):
    line = lines[i]
    if not line.strip():
        continue
        
    # Lines at 12 spaces that should be 8 (method body level)
    if line.startswith('            ') and not line.startswith('                '):
        # Check if it's a simple statement or control flow at method level
        stripped = line.lstrip()
        if (stripped.startswith('return ') or stripped.startswith('raise ') or
            stripped.startswith('break') or stripped.startswith('continue') or
            stripped.startswith('pass') or stripped.startswith('yield ') or
            stripped.startswith('if ') or stripped.startswith('for ') or
            stripped.startswith('while ') or stripped.startswith('try:') or
            stripped.startswith('except ') or stripped.startswith('else:') or
            stripped.startswith('elif ') or stripped.startswith('with ') or
            stripped.startswith('async for ') or stripped.startswith('async with ') or
            stripped.startswith('log.') or stripped.startswith('self.') or
            stripped.startswith('reports') or stripped.startswith('all_data') or
            stripped.startswith('filtered') or stripped.startswith('detail') or
            stripped.startswith('series') or stripped.startswith('row') or
            stripped.startswith('date_range') or stripped.startswith('days') or
            stripped.startswith('start') or stripped.startswith('end') or
            stripped.startswith('client_id') or stripped.startswith('report') or
            stripped.startswith('template') or stripped.startswith('updates') or
            stripped.startswith('key') or stripped.startswith('value') or
            stripped.startswith('offset') or stripped.startswith('limit') or
            stripped.startswith('offset:') or stripped.startswith('limit:') or
            stripped.startswith('days =') or stripped.startswith('start =') or
            stripped.startswith('end =')):
            lines[i] = '        ' + stripped

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed method body statements')