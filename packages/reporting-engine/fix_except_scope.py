with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix _execute_data_source - move return inside except block
# Lines 523-532 (0-indexed: 522-531)
# Current structure:
# 522: except Exception as e:
# 523:     log.exception(...)
# 524: return QueryResult(...)  # outside except!
# Need to indent return to be inside except

lines[522] = '        except Exception as e:\n'
lines[523] = '            log.exception("query_failed", source_type=getattr(source.type, \'value\', source.type), error=str(e))\n'
lines[524] = '            return QueryResult(\n'
lines[525] = '                data=[],\n'
lines[526] = '                columns=[],\n'
lines[527] = '                row_count=0,\n'
lines[528] = '                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),\n'
lines[529] = '                source=source.type,\n'
lines[530] = '                metadata={"error": str(e)},\n'
lines[531] = '            )\n'
# Remove the old return lines (525-532 old)
# Lines 525-532 old are now at 532-539, need to remove them
del lines[532:540]

with open(r'C:\Users\IhorLeshchuk\PycharmProjects\retention-analytics-platform\packages\reporting-engine\src\reporting_engine\service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed except block scoping')