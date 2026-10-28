with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 397 (0-indexed: 396) - should be 12 spaces
lines[396] = '            log.info("report_run_completed", run_id=run.id, \n'
lines[397] = '                widgets=run.widgets_rendered, failed=run.widgets_failed,\n'
lines[398] = '                formats=len(output_files))\n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed line 397')