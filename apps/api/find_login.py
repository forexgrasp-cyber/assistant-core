with open('app/api/v1/auth.py') as f:
    content = f.read()
    idx = content.find('@router.post("/login"')
    if idx >= 0:
        print(content[idx:idx+500])