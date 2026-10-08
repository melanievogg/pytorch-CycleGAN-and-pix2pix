#!/usr/bin/env python3
"""Build an offline, unpaired CycleGAN visual QC gallery (standard library only)."""
import argparse
import csv
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

KINDS = ('real_A', 'fake_B', 'rec_A', 'idt_B', 'real_B', 'fake_A', 'rec_B', 'idt_A')
SUFFIX = re.compile(r'^(?P<base>.+)_(?P<kind>' + '|'.join(KINDS) + r')$')
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}


def extract_basename(path):
    match = SUFFIX.fullmatch(Path(path).stem)
    return (match['base'], match['kind']) if match else None


def find_result_images(root, recursive=False):
    return sorted((p for p in (root.rglob('*') if recursive else root.iterdir())
                   if p.is_file() and p.suffix.lower() in EXTENSIONS and extract_basename(p)),
                  key=lambda p: p.as_posix())


def parse_metadata(basename):
    metadata = {}
    for key, pattern in (('subject', r'(?:^|_)subject(\d+)(?=_|$)'),
                         ('eye', r'(?:^|_)(OS|OD|OU)(?=_|$)'),
                         ('bscan', r'(?:^|_)bscan_(\d+)(?=_|$)')):
        match = re.search(pattern, basename, re.IGNORECASE)
        if match:
            metadata[key] = match[1].upper() if key == 'eye' else match[1]
    return metadata


def natural_key(value):
    return tuple((0, int(s)) if s.isdigit() else (1, s.casefold())
                 for s in re.split(r'(\d+)', value))


def group_images(paths, root):
    groups = {}
    for path in paths:
        base, kind = extract_basename(path)
        # Keep repeated basenames in separate recursive subdirectories distinct.
        parent = path.parent.relative_to(root).as_posix()
        key = base if parent == '.' else parent + '/' + base
        group = groups.setdefault(key, {'id': key, 'basename': base, 'images': {},
                                        **parse_metadata(base)})
        if kind in group['images']:
            raise ValueError(f'Ambiguous duplicate for {key} / {kind}: '
                             f'{group["images"][kind]} and {path}')
        group['images'][kind] = path
    values = list(groups.values())
    if values and all(all(k in g for k in ('subject', 'eye', 'bscan')) for g in values):
        values.sort(key=lambda g: (int(g['subject']), g['eye'].upper(), int(g['bscan']), g['id']))
    else:
        values.sort(key=lambda g: (natural_key(g['id']), g['id']))
    for group in values:
        group['complete_group'] = all(k in group['images'] for k in KINDS)
    return values


def write_manifest(groups, path):
    fields = ['basename', 'case_id', 'subject', 'eye', 'bscan'] + [k + '_path' for k in KINDS] + ['complete_group']
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for g in groups:
            writer.writerow({**{k: g.get(k, '') for k in ('basename', 'subject', 'eye', 'bscan', 'complete_group')},
                             'case_id': g['id'], **{k + '_path': str(g['images'].get(k, '')) for k in KINDS}})


def write_missing_report(groups, path):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['basename', 'case_id', 'missing_type'])
        for g in groups:
            for kind in KINDS:
                if kind not in g['images']:
                    writer.writerow([g['basename'], g['id'], kind])


def build_html(groups, output, title, dataset_id):
    cases = []
    assets = output / 'images'
    assets.mkdir(exist_ok=True)
    for g in groups:
        case = {k: v for k, v in g.items() if k != 'images'}
        case['images'] = {}
        for kind, source in g['images'].items():
            name = hashlib.sha256(g['id'].encode()).hexdigest() + '_' + kind + source.suffix.lower()
            target = assets / name
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            case['images'][kind] = 'images/' + name
        cases.append(case)
    payload = json.dumps({'cases': cases, 'kinds': KINDS, 'dataset': dataset_id}, ensure_ascii=True).replace('<', '\\u003c')
    return TEMPLATE.replace('__TITLE__', html.escape(title)).replace('__DATA__', payload)


TEMPLATE = r'''<!doctype html>
<html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
*{box-sizing:border-box}body{margin:20px;background:#14181e;color:#edf0f5;font:15px system-ui,sans-serif}h1{font-size:23px}button,select,input{font:inherit;padding:7px;border:1px solid #718096;border-radius:4px;background:#252d38;color:inherit}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #71bbff}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0}#caseTitle{overflow-wrap:anywhere}#panels{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.panel{margin:0;background:#202733;border:1px solid #465366;border-radius:5px;overflow:hidden}.panel figcaption{padding:8px;font-weight:600}.imagebox{height:clamp(130px,22vw,310px);display:flex;align-items:center;justify-content:center;background:#080a0c}.imagebox button{width:100%;height:100%;padding:0;border:0;background:none}.imagebox img{width:100%;height:100%;object-fit:contain}.missing{color:#ffbb80}.qc{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:18px}.rating{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px;background:#202733;flex-wrap:wrap}.rating button{font-size:12px;margin-left:4px}.rating button[aria-pressed=true]{outline:2px solid #fff;background:#365975}.rating button[data-value=FAIL][aria-pressed=true]{background:#9d3030}.rating button[data-value=SUSPICIOUS][aria-pressed=true]{background:#795817}details{margin:12px 0;color:#c5d0df}li{margin:5px 0}dialog{max-width:96vw;max-height:96vh;background:#14181e;color:white;border:1px solid #718096;padding:15px}dialog::backdrop{background:#000c}#zoomScroll{overflow:auto;max-height:78vh;max-width:90vw}#zoomImage{display:block;max-width:100%;max-height:75vh;object-fit:contain}#zoomImage.original{max-width:none;max-height:none}#storageWarning{color:#ffbb80}#jump{width:90px}@media(max-width:750px){#panels{grid-template-columns:repeat(2,minmax(0,1fr))}.qc{grid-template-columns:1fr}}@media(max-width:420px){#panels{grid-template-columns:1fr}}
</style>
<h1>__TITLE__</h1>
<p>Unpaired CycleGAN: real_B ist <strong>keine pixelweise Ground Truth</strong> für fake_B; real_A ist keine für fake_A. Beurteile Anatomieerhalt und plausiblen Domainwechsel.</p>
<details><summary>Help: Bildtypen und visuelle QC</summary>
<ul><li>real_A: Originalbild aus Domain A → fake_B: Translation nach B → rec_A: Rekonstruktion A → B → A.</li>
<li>real_B: Originalbild aus Domain B → fake_A: Translation nach A → rec_B: Rekonstruktion B → A → B.</li>
<li>idt_B: Identity-Ausgabe für real_B. idt_A: Identity-Ausgabe für real_A.</li>
<li>A / D: Bleibt die Anatomie von real_A → fake_B bzw. real_B → fake_A erhalten?</li>
<li>B / E: Wirken fake_B bzw. fake_A stilistisch plausibel wie die jeweilige Zieldomain?</li>
<li>C / F: Bleiben real_B vs. idt_B bzw. real_A vs. idt_A weitgehend unverändert?</li>
<li>G: Stellen rec_A und rec_B die ursprünglichen Strukturen plausibel wieder her?</li></ul>
<p>Links/Rechts navigiert; Bild anklicken öffnet Zoom, Escape oder Hintergrundklick schließt ihn. „Original (1:1)“ zeigt natürliche Bildpixel mit Scrollen. Anzeigegrößen ändern nur die Browserdarstellung.</p>
<p>Bewertungen werden pro Datensatz in diesem Browser gespeichert. Erneutes Anklicken hebt eine Bewertung auf. Für dauerhafte Sicherung regelmäßig JSON exportieren; Browser, Adresse oder Port wechseln kann einen anderen lokalen Speicher verwenden.</p></details>
<div class="toolbar"><label>Subject <select id="subjectFilter"><option value="all">Alle Subjects</option></select></label><label>Gruppen <select id="completeness"><option value="all">Alle</option><option value="complete">Vollständig</option><option value="missing">Unvollständig</option></select></label>
<label>Overall <select id="ratingFilter"><option value="all">Alle</option><option>PASS</option><option>SUSPICIOUS</option><option>FAIL</option><option value="unrated">Unbewertet</option></select></label><button id="export">Export QC ratings (JSON)</button></div>
<p id="storageWarning" role="status"></p>
<h2 id="caseTitle"></h2><div class="toolbar"><button id="first">First</button><button id="previous">Previous</button><span id="position" aria-live="polite"></span><button id="next">Next</button><button id="last">Last</button><label>Fallnummer <input id="jump" type="number" min="1"></label></div>
<main id="panels"></main><section id="ratings" class="qc" aria-label="QC ratings"></section>
<dialog id="zoom"><div class="toolbar"><strong id="zoomTitle"></strong><button id="sizeToggle">Original (1:1)</button><button id="closeZoom">Schließen</button></div><div id="zoomScroll"><img id="zoomImage" alt=""></div></dialog>
<script id="data" type="application/json">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const subjects=[...new Set(data.cases.map(c=>c.subject).filter(Boolean))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
for(const subject of subjects){const option=document.createElement('option');option.value=subject;option.textContent='Subject '+subject;$('subjectFilter').append(option);}
if(data.cases.some(c=>!c.subject)){const option=document.createElement('option');option.value='unknown';option.textContent='Ohne Subject';$('subjectFilter').append(option);}
const aspects=[['a_anatomy','A) A → B anatomy preservation'],['b_appearance','B) B-domain appearance of fake_B'],['b_identity','C) B identity (real_B vs idt_B)'],['b_anatomy','D) B → A anatomy preservation'],['a_appearance','E) A-domain appearance of fake_A'],['a_identity','F) A identity (real_A vs idt_A)'],['cycle','G) Cycle consistency'],['overall','Overall']];
const values=['PASS','SUSPICIOUS','FAIL'],storageKey='cyclegan-qc-v1:'+data.dataset;
let ratings=Object.create(null),visible=[],index=0;
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'{}');if(saved&&typeof saved==='object'&&!Array.isArray(saved)){for(const c of data.cases){if(!Object.hasOwn(saved,c.id))continue;const r=saved[c.id];if(!r||typeof r!=='object')continue;ratings[c.id]={};for(const [key] of aspects)if(values.includes(r[key]))ratings[c.id][key]=r[key];}}}catch(e){$('storageWarning').textContent='Lokaler Speicher nicht verfügbar oder ungültig. Bewertungen bleiben vorerst nur im Arbeitsspeicher; bitte exportieren.';}
function save(){try{localStorage.setItem(storageKey,JSON.stringify(ratings));}catch(e){$('storageWarning').textContent='Speichern im Browser fehlgeschlagen. Bitte Bewertungen vor dem Schließen exportieren.';}}
function filter(keep){visible=data.cases.filter(c=>($('subjectFilter').value==='all'||($('subjectFilter').value==='unknown'?!c.subject:c.subject===$('subjectFilter').value))&&($('completeness').value==='all'||c.complete_group===($('completeness').value==='complete'))&&($('ratingFilter').value==='all'||($('ratingFilter').value==='unrated'?!ratings[c.id]?.overall:ratings[c.id]?.overall===$('ratingFilter').value)));const found=visible.findIndex(c=>c.id===keep);index=found>=0?found:Math.min(index,Math.max(0,visible.length-1));render();}
function move(n){index=Math.max(0,Math.min(visible.length-1,n));render();}
function render(){const c=visible[index];$('panels').replaceChildren();$('ratings').replaceChildren();$('position').textContent=visible.length?`${index+1} / ${visible.length} (${data.cases.length} gesamt)`:'0 / 0';$('previous').disabled=$('first').disabled=!c||index===0;$('next').disabled=$('last').disabled=!c||index===visible.length-1;$('jump').disabled=!c;$('jump').max=visible.length;$('jump').value=c?index+1:'';$('caseTitle').textContent=c?c.id:'Keine Fälle für diese Auswahl';if(!c)return;
if(c.subject)$('caseTitle').textContent+=` — Subject ${c.subject} | ${c.eye||'—'} | B-scan ${c.bscan||'—'}`;
for(const kind of data.kinds){const panel=document.createElement('figure'),caption=document.createElement('figcaption'),box=document.createElement('div');panel.className='panel';caption.textContent=kind;box.className='imagebox';if(c.images[kind]){const button=document.createElement('button'),img=document.createElement('img');button.setAttribute('aria-label',kind+' vergrößern');img.src=c.images[kind];img.alt=kind+' — '+c.basename;img.onerror=()=>{box.textContent='missing / Bild nicht lesbar';box.classList.add('missing');};button.append(img);button.onclick=()=>{ $('zoomTitle').textContent=c.basename+' / '+kind;$('zoomImage').src=img.src;$('zoomImage').alt=img.alt;$('zoomImage').classList.remove('original');$('sizeToggle').textContent='Original (1:1)';$('zoom').showModal();};box.append(button);}else{box.textContent='missing';box.classList.add('missing');}panel.append(caption,box);$('panels').append(panel);}
for(const [key,label] of aspects){const row=document.createElement('div'),name=document.createElement('span'),buttons=document.createElement('div');row.className='rating';row.setAttribute('role','group');row.setAttribute('aria-label',label);name.textContent=label;for(const value of values){const b=document.createElement('button');b.textContent=value;b.dataset.value=value;b.setAttribute('aria-pressed',String(ratings[c.id]?.[key]===value));b.onclick=()=>{ratings[c.id]??={};if(ratings[c.id][key]===value)delete ratings[c.id][key];else ratings[c.id][key]=value;save();filter(c.id);};buttons.append(b);}row.append(name,buttons);$('ratings').append(row);}}
$('previous').onclick=()=>move(index-1);$('next').onclick=()=>move(index+1);$('first').onclick=()=>move(0);$('last').onclick=()=>move(visible.length-1);$('jump').onchange=()=>{const n=Number($('jump').value);if(Number.isInteger(n)&&n>=1)move(n-1);};for(const id of ['subjectFilter','completeness','ratingFilter'])$(id).onchange=()=>{index=0;filter();};
document.addEventListener('keydown',e=>{if($('zoom').open||['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;if(e.key==='ArrowLeft'){e.preventDefault();move(index-1);}if(e.key==='ArrowRight'){e.preventDefault();move(index+1);}});
$('closeZoom').onclick=()=>$('zoom').close();$('zoom').onclick=e=>{const r=$('zoom').getBoundingClientRect();if(e.target===$('zoom')&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))$('zoom').close();};$('sizeToggle').onclick=()=>{$('zoomImage').classList.toggle('original');$('sizeToggle').textContent=$('zoomImage').classList.contains('original')?'An Fenster anpassen':'Original (1:1)';};
$('export').onclick=()=>{const result={schema_version:1,dataset:data.dataset,exported_at:new Date().toISOString(),cases:data.cases.map(c=>({case_id:c.id,basename:c.basename,subject:c.subject||null,eye:c.eye||null,bscan:c.bscan||null,complete_group:c.complete_group,missing:data.kinds.filter(k=>!c.images[k]),ratings:Object.fromEntries(aspects.map(([key])=>[key,ratings[c.id]?.[key]||null]))}))};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='cyclegan_qc_ratings.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);};filter();
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--title', default='CycleGAN viewer')
    parser.add_argument('--recursive', action='store_true')
    args = parser.parse_args()
    root, output = args.results_dir.resolve(), args.output_dir.resolve()
    if not root.is_dir():
        parser.error(f'Results directory does not exist: {root}')
    if root == output or root in output.parents or output in root.parents:
        parser.error('Input and output must be separate, non-nested directories.')
    try:
        groups = group_images(find_result_images(root, args.recursive), root)
        if not groups:
            parser.error('No supported CycleGAN images found (expected <basename>_real_A.png etc.).')
        output.mkdir(parents=True, exist_ok=True)
        page = build_html(groups, output, args.title, hashlib.sha256(str(root).encode()).hexdigest())
        write_manifest(groups, output / 'viewer_manifest.csv')
        write_missing_report(groups, output / 'missing_files.csv')
        (output / 'index.html').write_text(page, encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')
    complete = sum(g['complete_group'] for g in groups)
    print(f'Vollständige Achtergruppen: {complete}\nUnvollständige Gruppen: {len(groups) - complete}')
    for name in ('index.html', 'viewer_manifest.csv', 'missing_files.csv'):
        print(output / name)


if __name__ == '__main__':
    main()
