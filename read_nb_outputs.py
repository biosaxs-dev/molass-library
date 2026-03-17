import json
with open('study/scipy_inspect_issue.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code' and cell.get('outputs'):
        ec = cell.get('execution_count', '?')
        print(f'=== Cell {i+1} (exec #{ec}) ===')
        for out in cell['outputs']:
            if out.get('output_type') == 'stream':
                print(''.join(out['text']))
            elif out.get('output_type') == 'error':
                print('ERROR:', out['ename'], out['evalue'])
