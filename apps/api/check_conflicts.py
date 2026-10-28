import re
import os

for root, dirs, files in os.walk('app/models'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fp:
                content = fp.read()
                indexes = re.findall(r'Index\(["\']([^"\']+)', content)
                for idx in indexes:
                    if 'verification_token' in idx or 'key_id' in idx:
                        print(f'{path}: {idx}')