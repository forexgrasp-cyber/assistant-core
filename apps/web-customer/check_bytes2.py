with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\apps\web-customer\src\app\login\page.tsx', 'rb') as f:
    content = f.read()

# Check around the problematic area
for i in range(4000, 4100):
    if i < len(content):
        b = content[i]
        print(f'Offset {i}: {b} ({chr(b) if b >= 32 else "ctrl"})')