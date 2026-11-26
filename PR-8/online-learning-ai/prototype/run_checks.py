"""Run the demonstration fixtures, produce the notebook and evaluation artifacts."""

from pathlib import Path
from contextlib import redirect_stdout
from html import escape
import csv
import io
import json
import sys
from risk import assess, route

work = Path(__file__).parent
NAMES = {'monitor':'Моніторинг', 'review':'Звичайний огляд',
         'priority':'Пріоритетний огляд', 'unavailable':'Оцінка недоступна',
         'risk':'Ризик', 'no_risk':'Без ризику'}

def rows(name):
    with (work / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

def export_csv(name, data):
    with (work / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)

def test_cases(name, extended):
    output = []
    for case in rows(name):
        result = assess(case)
        actual_route = route(result)
        predicted = {'monitor': 'no_risk', 'unavailable': 'unavailable'}.get(actual_route, 'risk')
        expected = case['expected'] if extended else case['expected_route']
        actual = predicted if extended else actual_route
        record = dict(case, risk_score=result['risk_score'], route=actual_route,
                      predicted=actual, correct=actual == expected, reason=result['reason'])
        output.append(record)
    return output

def fixture_markdown(data, extended):
    lines = []
    for r in data:
        score = '—' if r['risk_score'] is None else f"{r['risk_score']:.2f}".replace('.',',')
        actual = f"{score} · {NAMES[r['route']]}"
        check = 'так' if r['correct'] else 'помилка'
        if extended:
            values = (r['case_id'], NAMES[r['expected']], actual, check)
        else:
            inputs = ', '.join([r['test_score'] or '—', r['course_completion'],
                                'так' if r['task_completed']=='true' else 'ні', r['study_time']])
            values = (r['case_id'] + ' · ' + inputs, NAMES[r['expected_route']], actual, check)
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)

def screenshot_source(title, subtitle, summary, data, extended):
    if extended:
        head = ['Випадок', 'Очікувана мітка', 'Індекс і маршрут', 'Перевірка']
    else:
        head = ['Випадок та вхідні ознаки', 'Очікуваний маршрут', 'Індекс і маршрут', 'Перевірка']
    table = '<tr>' + ''.join('<th>'+escape(h)+'</th>' for h in head) + '</tr>'
    body = fixture_markdown(data, extended).splitlines()
    for line in body:
        cols = [item.strip() for item in line.strip('|').split('|')]
        css = ' class="error"' if cols[-1] == 'помилка' else ''
        table += '<tr'+css+'>' + ''.join('<td>'+escape(c)+'</td>' for c in cols) + '</tr>'
    content = f"""<!doctype html><html lang="uk"><meta charset="utf-8"><title>{escape(title)}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#f0f4f7;color:#14293a;font:24px Arial,sans-serif}}
main{{margin:44px auto;width:1300px;background:white;border:2px solid #c9d7e0;border-radius:20px;padding:40px 46px}}
h1{{font-size:44px;margin:0 0 12px}} p{{margin:0 0 22px;line-height:1.4}}
strong{{display:block;background:#ecf5ef;border-left:7px solid #277247;padding:13px 18px;margin:0 0 22px}}
table{{width:100%;border-collapse:collapse;font-size:23px}} th,td{{text-align:left;padding:11px 14px;border-bottom:1px solid #d8e0e6}}
th{{background:#eaf2fa}} .error{{background:#fff0e8}}
</style><main><h1>{escape(title)}</h1><p>{escape(subtitle)}</p><strong>{escape(summary)}</strong>
<table>{table}</table></main></html>"""
    return content

def notebook(data):
    def markdown(src):
        return dict(cell_type='markdown', metadata={}, source=src)
    def code(src):
        return dict(cell_type='code', metadata={}, source=src, execution_count=None, outputs=[])
    model = (work / 'risk.py').read_text(encoding='utf-8')
    samples = (work / 'smoke.csv').read_text(encoding='utf-8')
    checks = '''import csv
from io import StringIO

samples = list(csv.DictReader(StringIO(SAMPLES.strip())))
checks = []
for case in samples:
    result = assess(case)
    decision = route(result)
    ok = decision == case['expected_route']
    checks.append(ok)
    detail = result['reason'] or ''
    print(f"{case['case_id']}  {result['risk_score']!s:>5}  {decision:12}  "
          f"очікувано: {case['expected_route']:12}  {'так' if ok else 'НІ'}  {detail}")
print(f"\\nЗбіг маршрутів: {sum(checks)}/{len(checks)} ({sum(checks)/len(checks):.0%})")
assert all(checks)
print("Складові сценарію S02:", assess(samples[1])['factors'])'''
    cells = [
        markdown('# Прототип раннього виявлення навчального ризику\n'
                 'Практична робота №6. Інтелектуальна система онлайн-освіти. '
                 'Кожна клітинка працює в Python 3 зі стандартною бібліотекою. '
                 'Запустіть усі клітинки послідовно. Приклади синтетичні.'),
        markdown('## Компонент C6 і правила розгляду C7\n'
                 'Індекс є зваженим балом, а 45 і 60 визначають маршрути. '
                 'Звернення щодо підтримки потребує рішення викладача.'),
        code(model),
        markdown('## Тестові записи і фактична перевірка\n'
                 'Очікувані маршрути задані заздалегідь. S04 і S05 перевіряють рівність порогам, '
                 'S06 перевіряє допустимість нульової активності, S07 і S08 — відмову.'),
        code('SAMPLES = ' + repr(samples) + '\n\n' + checks),
        markdown('## Висновок\n'
                 'Збіг маршрутів на цих прикладах підтверджує працездатність логіки. '
                 'Прогностичну якість потрібно оцінювати окремо.')
    ]
    kernel = {}
    count = 0
    for idx, cell in enumerate(cells):
        cell['id'] = 'cell-' + str(idx + 1)
        if cell['cell_type'] == 'code':
            count += 1
            cell['execution_count'] = count
            std = io.StringIO()
            with redirect_stdout(std):
                exec(compile(cell['source'], f'<cell-{idx+1}>', 'exec'), kernel)
            if std.getvalue():
                cell['outputs'] = [dict(output_type='stream', name='stdout', text=std.getvalue())]
    assert kernel['checks'] == [r['correct'] for r in data]
    return dict(cells=cells, metadata={'kernelspec': {'display_name': 'Python 3',
                 'language': 'python', 'name': 'python3'}, 'language_info': {'name':'python'}},
                nbformat=4, nbformat_minor=5)

def extended_results(data):
    valid = [r for r in data if r['expected'] != 'unavailable']
    tp = sum(r['expected']=='risk' and r['predicted']=='risk' for r in valid)
    fp = sum(r['expected']=='no_risk' and r['predicted']=='risk' for r in valid)
    tn = sum(r['expected']=='no_risk' and r['predicted']=='no_risk' for r in valid)
    fn = sum(r['expected']=='risk' and r['predicted']=='no_risk' for r in valid)
    invalid = [r for r in data if r['expected'] == 'unavailable']
    assert tp + fp + tn + fn == len(valid)
    assert all(r['correct'] for r in invalid)
    return dict(tp=tp,fp=fp,tn=tn,fn=fn,accuracy=(tp+tn)/len(valid),precision=tp/(tp+fp),
                recall=tp/(tp+fn),valid=len(valid),validation_passed=len(invalid))

def main(mode):
    extended = mode == 'extended'
    name = 'evaluation' if extended else 'smoke'
    data = test_cases(name+'.csv', extended)
    export_csv(name+'_results.csv', data)
    (work / (name+'_rows.txt')).write_text(fixture_markdown(data, extended), encoding='utf-8')
    if extended:
        metrics = extended_results(data)
        print(json.dumps(metrics, ensure_ascii=False))
        errors = [r for r in data if not r['correct']]
        summary = (f"Точність {metrics['accuracy']:.2%}  •  Precision {metrics['precision']:.2%}  "
                   f"•  Повнота {metrics['recall']:.2%}  •  Відмова {metrics['validation_passed']}/2")
        (work/'evaluation_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
        html = screenshot_source('Розширена перевірка компонента C6',
                'ПР-7 · rules-1.0 · 18 синтетичних записів · Рядки з помилковим прогнозом',
                summary, errors, True)
    else:
        hits = sum(r['correct'] for r in data)
        print(f'{hits}/{len(data)} routes match')
        nb = notebook(data)
        (work/'risk_prototype.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n',
                                                 encoding='utf-8')
        html = screenshot_source('Перевірка прототипу навчального ризику',
                'ПР-6 · rules-1.0 · Ознаки в порядку: бал, прогрес %, виконане завдання, хвилини',
                f'Збіг маршрутів {hits}/{len(data)}  •  {hits/len(data):.0%}', data, False)
    (work/(name+'.html')).write_text(html, encoding='utf-8')

if __name__ == '__main__':
    main(sys.argv[1])
