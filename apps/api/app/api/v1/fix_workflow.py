with open('C:\\Users\\IhorLeshchuk\\PycharmProjects\\retention-analytics-platform-clean\\apps\\api\\app\\api\\v1\\workflows.py', 'r') as f:
    content = f.read()
content = content.replace(
    'client_id=current_user.client_id,\n        name=workflow_data.get("name")',
    'agency_id=current_user.client_id,\n        name=workflow_data.get("name")'
)
with open('C:\\Users\\IhorLeshchuk\\PycharmProjects\\retention-analytics-platform-clean\\apps\\api\\app\\api\\v1\\workflows.py', 'w') as f:
    f.write(content)
print('Done')