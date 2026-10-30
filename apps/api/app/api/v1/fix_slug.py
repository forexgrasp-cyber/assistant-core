with open('workflows.py', 'r') as f:
    content = f.read()
content = content.replace(
    'name=workflow_data.get("name"),\n        description=workflow_data.get("description")',
    'name=workflow_data.get("name"),\n        agency_id=current_user.client_id,\n        description=workflow_data.get("description")'
)
with open('workflows.py', 'w') as f:
    f.write(content)
print('Done')