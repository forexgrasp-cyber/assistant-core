with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _render_report method for loops
# Line 878 (0-indexed: 877) - if not self._evaluate_conditions... should be at 12
lines[877] = '            if not self._evaluate_conditions(section.conditions, context):\n'
# Line 881 (0-indexed: 880) - rendered_widgets = [] should be at 12
lines[880] = '            rendered_widgets = []\n'
# Line 883 (0-indexed: 882) - for widget in section.widgets: at 8, body at 16 (correct)
# Line 885 (0-indexed: 884) - if not self._evaluate_conditions... at 16 (inside widget for) - correct
# Line 888 (0-indexed: 887) - try: at 16, body at 20 (correct)

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _render_report')