with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Properly fix indentation: control flow at indent N, body at indent N+4
for i in range(len(lines) - 1):
    line = lines[i]
    
    stripped = line.strip()
    
    # Control flow statements that start a block
    is_control = (stripped.startswith('if ') or stripped.startswith('for ') or 
                  stripped.startswith('while ') or stripped.startswith('try:') or
                  stripped.startswith('except ') or stripped.startswith('else:') or
                  stripped.startswith('elif ') or stripped.startswith('with ') or
                  stripped.startswith('async for ') or stripped.startswith('async with ') or
                  stripped.startswith('def ') or stripped.startswith('async def '))
    
    if is_control and line.strip().endswith(':'):
        current_indent = len(line) - len(line.lstrip())
        # Next non-empty line should be at current_indent + 4
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines):
            next_indent = len(lines[j]) - len(lines[j].lstrip())
            expected = current_indent + 4
            if next_indent < expected:
                # Need to add indentation to body
                for k in range(j, len(lines)):
                    if not lines[k].strip():
                        continue
                    body_indent = len(lines[k]) - len(lines[k].lstrip())
                    if body_indent < expected:
                        break
                    if body_indent < expected:
                        lines[k] = ' ' * (expected - body_indent) + lines[k]
                    else:
                        # Already at or beyond expected, add the difference
                        lines[k] = ' ' * (expected - current_indent) + lines[k]

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed control flow bodies')