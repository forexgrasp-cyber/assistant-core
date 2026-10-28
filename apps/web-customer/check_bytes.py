with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\apps\web-customer\src\app\login\page.tsx', 'rb') as f:
    content = f.read()

for i in range(4000, 4500):
    if i < len(content):
        b = content[i]
        if b < 32 or b > 126:
            print(f'Offset {i}: {b} ({chr(b) if b >= 32 else "ctrl"})')