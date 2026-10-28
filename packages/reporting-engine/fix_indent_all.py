with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix ALL methods in the class - reduce method body indent by 4
# Class methods should be at indent 4, their bodies at 8, nested at 12, etc.
in_class = False
for i in range(len(lines)):
    line = lines[i]
    stripped = line.strip()
    
    # Track class boundaries
    if stripped.startswith('class '):
        in_class = True
        continue
    elif stripped and not line.startswith(' ') and in_class:
        # Left class
        in_class = False
        continue
    
    if not in_class:
        continue
        
    # Inside class - fix method bodies
    # Method defs at 4 spaces
    if line.startswith('    async def ') or line.startswith('    def '):
        # Method definition - correct at 4 spaces
        continue
    elif line.startswith('        ') and not line.startswith('            '):
        # Could be method body at 8 or nested at 12+
        # If it's a control flow statement (if, for, while, try, except, else, elif)
        stripped_line = line.lstrip()
        if (stripped_line.startswith('if ') or stripped_line.startswith('for ') or 
            stripped_line.startswith('while ') or stripped_line.startswith('try:') or
            stripped_line.startswith('except ') or stripped_line.startswith('else:') or
            stripped_line.startswith('elif ') or stripped_line.startswith('with ') or
            stripped_line.startswith('async for ') or stripped_line.startswith('async with ')):
            # These should be at 8 spaces (inside method)
            if line.startswith('        '):
                continue  # Already correct
        elif stripped_line.startswith('return ') or stripped_line.startswith('raise ') or \
             stripped_line.startswith('break') or stripped_line.startswith('continue') or \
             stripped_line.startswith('pass') or stripped_line.startswith('yield '):
            # Simple statements at 12 spaces (inside control flow)
            if line.startswith('            '):
                continue
            elif line.startswith('        '):
                lines[i] = '            ' + stripped_line
        else:
            # Regular statement inside method - should be at 8
            if line.startswith('            ') and not line.startswith('                '):
                # At 12, should be 8
                lines[i] = '        ' + stripped_line
    elif line.startswith('            ') and not line.startswith('                '):
        # At 12 spaces - could be inside if/for/try
        continue

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed all method bodies')