import re
import os

for root, dirs, files in os.walk('app/models'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fp:
                content = fp.read()
                indexes = re.findall(r'Index\(["\']([^"\']+)["\']', content)
                if indexes:
                    print(f'{path}: {indexes}')