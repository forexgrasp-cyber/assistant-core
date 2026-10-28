with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _generate_ai_summary method - for loop body over-indented by 4
# Lines 991-998 (0-indexed: 990-997) - reduce indent by 4
for i in range(990, 998):
    if lines[i].strip():
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if current_indent >= 12:
            lines[i] = lines[i][4:]

# Line 999 (0-indexed: 998) - should be at 8
lines[998] = '        summary_data["sections"].append(section_data)\n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _generate_ai_summary')