with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Simple fix: for each control flow at indent N, ensure body is at N+4
for i in range(len(lines)):
    line = lines[i]
    stripped = line.strip()
    
    # Check if this is a control flow statement ending with :
    if (stripped.startswith('if ') or stripped.startswith('for ') or 
        stripped.startswith('while ') or stripped.startswith('try:') or
        stripped.startswith('except ') or stripped.startswith('else:') or
        stripped.startswith('elif ') or stripped.startswith('with ') or
        stripped.startswith('async for ') or stripped.startswith('async with ')) and stripped.endswith(':'):
        
        current_indent = len(line) - len(line.lstrip())
        expected_body_indent = current_indent + 4
        
        # Find next non-empty line
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
            
        if j < len(lines):
            next_line = lines[j]
            next_indent = len(next_line) - len(next_line.lstrip())
            
            # If next line is at same or less indent than control, it needs fixing
            if next_indent <= current_indent:
                # Add indentation to the body
                lines[j] = ' ' * (expected_body_indent - next_indent) + next_line

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed control flow bodies')