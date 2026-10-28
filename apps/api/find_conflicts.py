import re
import os

# Find all columns with index=True (not unique)
for root, dirs, files in os.walk('app/models'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fp:
                content = fp.read()
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'index=True' in line and 'mapped_column' in line and 'unique=True' not in line:
                        match = re.match(r'\s*(\w+): Mapped', line)
                        if match:
                            col_name = match.group(1)
                            table_name = None
                            for j in range(i, -1, -1):
                                if '__tablename__' in lines[j]:
                                    match = re.search(r'__tablename__\s*=\s*["\']([^"\']+)["\']', lines[j])
                                    if match:
                                        table_name = match.group(1)
                                    break
                            if table_name:
                                expected_index = f'ix_{table_name}_{col_name}'
                                indexes = re.findall(r'Index\(["\']([^"\']+)', content)
                                for idx in indexes:
                                    if idx == expected_index:
                                        print(f'{path}:{i+1}: Column {col_name} has index=True, explicit index {idx} also exists')