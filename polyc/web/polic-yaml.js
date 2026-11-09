// Minimal deterministic YAML 1.2 serialization for PoliC's JSON-compatible schema.
// Strings are JSON-quoted (valid YAML double-quoted scalars); no dependencies or eval.
function scalar(value) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  throw new TypeError('Unsupported PoliC YAML value');
}
function block(value, indent = 0) {
  const prefix = ' '.repeat(indent);
  if (Array.isArray(value)) {
    if (!value.length) return '[]';
    return value.map(item => {
      const result = block(item, indent + 2);
      if (typeof item === 'object' && item !== null && (Array.isArray(item) ? item.length : Object.keys(item).length)) {
        return `${prefix}-\n${result}`;
      }
      return `${prefix}- ${result}`;
    }).join('\n');
  }
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) return '{}';
    return entries.map(([key, item]) => {
      if (!/^[A-Za-z_][A-Za-z0-9_-]*$/.test(key)) throw new TypeError('Unsupported PoliC YAML key');
      if (item !== null && typeof item === 'object' && (Array.isArray(item) ? item.length : Object.keys(item).length)) {
        return `${prefix}${key}:\n${block(item, indent + 2)}`;
      }
      return `${prefix}${key}: ${block(item, indent + 2)}`;
    }).join('\n');
  }
  return scalar(value);
}
export function asPolicYaml(constitution) {
  if (!constitution || constitution.kind !== 'NodeConstitution' || !constitution.spec) throw new TypeError('Not a PoliC constitution');
  return block(constitution) + '\n';
}
