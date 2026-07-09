# 任务：修复 parser 的空白处理

修改 parser，使其在返回解析结果前去掉首尾空白。

## 验收

- `parse_value("  miku  ")` 返回 `"miku"`
- 非空白相关行为保持不变
