with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _evaluate_conditions method - for loop body should be at indent 12
# Lines 943-966 (0-indexed: 942-965) - all should be at indent 12 (inside for loop at line 940)
for i in range(942, 966):
    if lines[i].strip():
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if current_indent == 8:
            lines[i] = '    ' + lines[i]
        elif current_indent == 13:  # blank lines at 13
            lines[i] = '            \n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _evaluate_conditions')