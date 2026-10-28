with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the _query_dimension_facts method for loops
# Line 648 (0-indexed: 647) - breakdown = ... should be at 12
lines[647] = '            breakdown = self.daily_facts.breakdown_counts(\n'
# Line 656 (0-indexed: 655) - for row in breakdown: - already at 8, body at 16 (correct)

# Also fix line 660 - filtered = ... should be at 8 (after the for loop)
# That's already correct

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _query_dimension_facts')