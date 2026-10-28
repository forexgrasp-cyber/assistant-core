with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _order_data method - nested function body
# Line 851 (0-indexed: 850) - def sort_key(row): at 8, body should be at 12
lines[851] = '            keys = []\n'
lines[852] = '            for o in order_by:\n'
lines[853] = '                field = o.get("field")\n'
lines[854] = '                direction = o.get("dir", "asc")\n'
lines[855] = '                val = row.get(field, 0)\n'
lines[856] = '                if direction == "desc":\n'
lines[857] = '                    val = -val if isinstance(val, (int, float)) else val\n'
lines[858] = '                keys.append(val)\n'
lines[859] = '            return tuple(keys)\n'
lines[860] = '        return sorted(data, key=sort_key)\n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _order_data')