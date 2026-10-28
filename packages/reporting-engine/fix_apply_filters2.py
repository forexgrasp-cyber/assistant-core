with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _apply_filters - remaining elif/return should be at indent 12 (inside for)
# Line 811 (0-indexed: 810) - elif between at 12
lines[810] = '            elif operator == "between":\n'
# Line 815 (0-indexed: 814) - return result at 8 (after for loop)
lines[814] = '        return result\n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _apply_filters end')