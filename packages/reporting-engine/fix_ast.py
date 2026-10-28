with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Use ast to parse and then regenerate with correct formatting
import ast
import sys

try:
    tree = ast.parse(content)
    # Use ast.unparse (Python 3.9+) to regenerate
    fixed = ast.unparse(tree)
    
    with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
        f.write(fixed)
    print('Fixed using ast.unparse')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()