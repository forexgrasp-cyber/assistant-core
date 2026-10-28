with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _render_report method - inner for loop at line 883 (0-indexed: 882)
# Outer for is at indent 8, so inner for should be at 12, its body at 16, etc.

# Line 883 (0-indexed: 882) - for widget... should be at 12
lines[882] = '            for widget in section.widgets:\n'

# Lines 884-906 (0-indexed: 883-905) - add 4 spaces to each (they're at 16, 20, etc. should be 20, 24, etc.)
for i in range(883, 906):
    if lines[i].strip():
        lines[i] = '    ' + lines[i]

# Line 907 (0-indexed: 906) - blank line should be at 12
lines[906] = '            \n'

# Line 915 (0-indexed: 914) - blank line should be at 8
lines[914] = '        \n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _render_report inner for loop')