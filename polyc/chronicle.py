"""Chronicle: plain language grounded exclusively in recorded coordinator events."""
def describe(report: dict) -> str:
    projects = report['projects']
    node = report['node_id']
    if not projects:
        intro = f'{node}: The cats report no completed tasks. They have offered no further explanation.'
    else:
        total = sum(x['tasks'] for x in projects)
        intro = f'{node}: completed {total} verified built-in CPU task(s) across {len(projects)} project(s).'
    lines = [intro]
    for project in projects:
        lines.append(f'  {project["job_id"]}: {project["tasks"]} tasks, '
                     f'{project["worker_wall_seconds"]:.3f} seconds measured worker wall time.')
    lines.append('No GPU use, electrical consumption, heat recovery, or revenue is inferred from these records.')
    return '\n'.join(lines)
