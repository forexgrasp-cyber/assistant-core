with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _cache_key method (lines 478-488, 0-indexed: 477-487)
# Method def at line 478 should be at 4, body at 8
lines[477] = '    def _cache_key(self, source: DataSourceConfig, context: ReportContext) -> str:\n'
lines[478] = '        """Generate cache key for a data source."""\n'
lines[479] = '        key_parts = [\n'
lines[480] = "            getattr(source.type, 'value', source.type),\n"
lines[481] = '            json.dumps(source.metrics, sort_keys=True),\n'
lines[482] = '            json.dumps(source.dimensions, sort_keys=True),\n'
lines[483] = '            json.dumps(source.filters, sort_keys=True),\n'
lines[484] = '            json.dumps(source.date_range, sort_keys=True),\n'
lines[485] = '            json.dumps(source.group_by, sort_keys=True),\n'
lines[486] = '        ]\n'
lines[487] = '        return "|".join(key_parts)\n'

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed _cache_key method')