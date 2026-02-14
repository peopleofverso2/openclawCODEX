---
name: archiscan-report
description: Generate professional architectural deliverables — PDF diagnostic reports, DXF annotated plans, quantity summaries, photo sheets. Use when asked to produce a report, export plans, create a deliverable, or compile scan results into a professional document.
---

# ArchiScan Report — Deliverable Generation

Compile scan data, measurements, and diagnostics into professional architectural documents.

## Report Types

| Type | Format | Content |
|---|---|---|
| Rapport de relevé | PDF | Plans, photos, métrés, observations |
| Plans cotés | DXF + SVG | Floor plans with dimensions |
| Fiche de métrés | PDF / CSV | Quantities for estimation |
| Diagnostic bâtiment | PDF | Pathologies, thermal, recommendations |
| Fiche photo | PDF | Grid of annotated photos |

## PDF Report Generation (WeasyPrint)

```bash
pip install weasyprint jinja2
```

### Report Template

```python
#!/usr/bin/env python3
"""Generate a professional ArchiScan PDF report."""
from jinja2 import Template
from weasyprint import HTML
from datetime import date
import json

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 20mm;
    @bottom-center { content: "ArchiScan — {{ project_name }} — Page " counter(page) " / " counter(pages); font-size: 9pt; color: #666; }
  }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; color: #333; line-height: 1.5; }
  h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 8px; font-size: 22pt; }
  h2 { color: #16213e; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 20px; font-size: 16pt; }
  h3 { color: #0f3460; font-size: 13pt; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10pt; }
  th { background: #16213e; color: white; padding: 8px; text-align: left; }
  td { padding: 6px 8px; border-bottom: 1px solid #eee; }
  tr:nth-child(even) { background: #f8f9fa; }
  .metric-box { display: inline-block; background: #f0f4f8; border-radius: 8px; padding: 12px 20px; margin: 5px; text-align: center; }
  .metric-value { font-size: 24pt; font-weight: bold; color: #16213e; }
  .metric-label { font-size: 9pt; color: #666; }
  .severity-alerte { color: #dc3545; font-weight: bold; }
  .severity-important { color: #fd7e14; font-weight: bold; }
  .severity-mineur { color: #28a745; }
  .photo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .photo-grid img { width: 100%; border: 1px solid #ddd; border-radius: 4px; }
  .page-break { page-break-before: always; }
  .info-table td:first-child { font-weight: bold; width: 200px; }
</style>
</head>
<body>

<h1>Rapport de Relevé Architectural</h1>
<h2>{{ project_name }}</h2>

<table class="info-table">
  <tr><td>Adresse</td><td>{{ address }}</td></tr>
  <tr><td>Date du relevé</td><td>{{ scan_date }}</td></tr>
  <tr><td>Date du rapport</td><td>{{ report_date }}</td></tr>
  <tr><td>Opérateur</td><td>{{ operator }}</td></tr>
  <tr><td>Équipement</td><td>{{ equipment }}</td></tr>
  <tr><td>Méthode</td><td>{{ method }}</td></tr>
</table>

<h2>Métriques Clés</h2>
<div>
  <div class="metric-box">
    <div class="metric-value">{{ metrics.surface_totale }}</div>
    <div class="metric-label">Surface totale (m²)</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ metrics.nb_pieces }}</div>
    <div class="metric-label">Pièces</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ metrics.surface_carrez }}</div>
    <div class="metric-label">Loi Carrez (m²)</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ metrics.hauteur_moyenne }}</div>
    <div class="metric-label">Hauteur moy. (m)</div>
  </div>
</div>

<div class="page-break"></div>
<h2>Plans</h2>
{% for plan in plans %}
<h3>{{ plan.title }}</h3>
<img src="{{ plan.svg_path }}" style="width:100%; border:1px solid #ddd;">
{% endfor %}

<div class="page-break"></div>
<h2>Tableau des Pièces</h2>
<table>
  <tr><th>Pièce</th><th>Surface (m²)</th><th>Hauteur (m)</th><th>Volume (m³)</th><th>Périmètre (m)</th></tr>
  {% for room in rooms %}
  <tr>
    <td>{{ room.name }}</td>
    <td>{{ room.area }}</td>
    <td>{{ room.height }}</td>
    <td>{{ room.volume }}</td>
    <td>{{ room.perimeter }}</td>
  </tr>
  {% endfor %}
</table>

<h2>Métrés</h2>
<table>
  <tr><th>Poste</th><th>Quantité</th><th>Unité</th></tr>
  {% for item in quantities %}
  <tr><td>{{ item.label }}</td><td>{{ item.value }}</td><td>{{ item.unit }}</td></tr>
  {% endfor %}
</table>

{% if issues %}
<div class="page-break"></div>
<h2>Diagnostic</h2>
<p>{{ issues | length }} point(s) relevé(s).</p>
<table>
  <tr><th>Catégorie</th><th>Sévérité</th><th>Constat</th><th>Recommandation</th></tr>
  {% for issue in issues %}
  <tr>
    <td>{{ issue.category }}</td>
    <td class="severity-{{ issue.severity | lower }}">{{ issue.severity }}</td>
    <td>{{ issue.finding }}</td>
    <td>{{ issue.recommendation }}</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

{% if photos %}
<div class="page-break"></div>
<h2>Planche Photos</h2>
<div class="photo-grid">
  {% for photo in photos %}
  <div>
    <img src="{{ photo.path }}">
    <p style="font-size:9pt; color:#666;">{{ photo.caption }}</p>
  </div>
  {% endfor %}
</div>
{% endif %}

</body>
</html>
"""

def generate_report(data, output="rapport_archiscan.pdf"):
    template = Template(REPORT_TEMPLATE)
    html_content = template.render(**data)

    # Write HTML (useful for debugging)
    with open(output.replace('.pdf', '.html'), 'w') as f:
        f.write(html_content)

    # Generate PDF
    HTML(string=html_content).write_pdf(output)
    print(f"Report generated: {output}")
```

### Usage

```python
data = {
    'project_name': 'Appartement 3 pièces — 15 rue de Rivoli',
    'address': '15 rue de Rivoli, 75001 Paris',
    'scan_date': '2026-02-10',
    'report_date': date.today().isoformat(),
    'operator': 'ArchiScan Bot',
    'equipment': 'iPhone 15 Pro (LiDAR) + DJI Mini 4 Pro',
    'method': 'LiDAR intérieur + photogrammétrie drone extérieur',
    'metrics': {
        'surface_totale': '65.3',
        'nb_pieces': '5',
        'surface_carrez': '62.1',
        'hauteur_moyenne': '2.80',
    },
    'plans': [
        {'title': 'Plan RDC', 'svg_path': 'plan_rdc.svg'},
    ],
    'rooms': [
        {'name': 'Salon', 'area': 22.5, 'height': 2.80, 'volume': 63.0, 'perimeter': 19.2},
        {'name': 'Cuisine', 'area': 10.2, 'height': 2.80, 'volume': 28.6, 'perimeter': 13.0},
        {'name': 'Chambre 1', 'area': 14.8, 'height': 2.80, 'volume': 41.4, 'perimeter': 15.6},
        {'name': 'Chambre 2', 'area': 11.3, 'height': 2.80, 'volume': 31.6, 'perimeter': 13.8},
        {'name': 'SDB', 'area': 6.5, 'height': 2.50, 'volume': 16.3, 'perimeter': 10.4},
    ],
    'quantities': [
        {'label': 'Murs — surface nette', 'value': '103.4', 'unit': 'm²'},
        {'label': 'Sols', 'value': '65.3', 'unit': 'm²'},
        {'label': 'Plafonds', 'value': '65.3', 'unit': 'm²'},
        {'label': 'Plinthes', 'value': '38.2', 'unit': 'ml'},
        {'label': 'Portes', 'value': '5', 'unit': 'u'},
        {'label': 'Fenêtres', 'value': '7', 'unit': 'u'},
    ],
    'issues': [
        {
            'category': 'Humidité',
            'severity': 'IMPORTANT',
            'finding': '2 zones humides détectées (SDB, cuisine)',
            'recommendation': 'Vérifier VMC et joints douche',
        },
    ],
    'photos': [
        {'path': 'photos/salon_01.jpg', 'caption': 'Salon — vue générale'},
        {'path': 'photos/cuisine_01.jpg', 'caption': 'Cuisine — vue depuis entrée'},
    ]
}

generate_report(data)
```

## CSV Quantity Export

```python
import csv

def export_quantities_csv(quantities, rooms, output="metres.csv"):
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Poste', 'Quantité', 'Unité'])

        # Room details
        writer.writerow([])
        writer.writerow(['--- PIÈCES ---', '', ''])
        for room in rooms:
            writer.writerow([room['name'], room['area'], 'm²'])

        # Global quantities
        writer.writerow([])
        writer.writerow(['--- MÉTRÉS GLOBAUX ---', '', ''])
        for q in quantities:
            writer.writerow([q['label'], q['value'], q['unit']])

    print(f"CSV export: {output}")
```

## DXF Annotated Plan Export

```python
import ezdxf

def export_annotated_plan(walls, rooms, openings, issues, output="plan_annote.dxf"):
    """Export floor plan with diagnostic annotations."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # Standard layers
    doc.layers.add("WALLS", color=7)
    doc.layers.add("ROOMS", color=2)
    doc.layers.add("DIMENSIONS", color=3)

    # Diagnostic layers
    doc.layers.add("DIAG_CRACKS", color=1)     # Red
    doc.layers.add("DIAG_MOISTURE", color=5)    # Blue
    doc.layers.add("DIAG_THERMAL", color=6)     # Magenta

    # Draw walls
    for wall in walls:
        msp.add_line(wall['start'], wall['end'],
                     dxfattribs={'layer': 'WALLS', 'lineweight': 50})

    # Room labels
    for room in rooms:
        msp.add_mtext(
            f"{room.get('name', f'Pièce {room[\"id\"]}')}\n{room['area_m2']} m²",
            dxfattribs={'layer': 'ROOMS', 'char_height': 0.15,
                        'insert': room['center']}
        )

    # Diagnostic annotations
    for issue in issues:
        if 'position' in issue:
            layer = f"DIAG_{issue['category'].upper()}"
            if layer not in [l.dxf.name for l in doc.layers]:
                layer = "DIAG_CRACKS"
            msp.add_circle(issue['position'], radius=0.3,
                          dxfattribs={'layer': layer})
            msp.add_mtext(
                issue.get('finding', issue.get('type', '?')),
                dxfattribs={'layer': layer, 'char_height': 0.08,
                            'insert': [issue['position'][0]+0.4,
                                       issue['position'][1]]}
            )

    doc.saveas(output)
    print(f"Annotated plan: {output}")
```

## Photo Sheet Generator

```python
def generate_photo_sheet(photos, output="planche_photos.pdf",
                          cols=2, title="Planche Photos"):
    """Generate a PDF photo contact sheet with captions."""
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
      @page {{ size: A4; margin: 15mm; }}
      body {{ font-family: Arial; }}
      h1 {{ font-size: 16pt; color: #333; }}
      .grid {{ display: grid; grid-template-columns: {'1fr ' * cols}; gap: 8px; }}
      .photo {{ text-align: center; }}
      .photo img {{ width: 100%; border: 1px solid #ccc; }}
      .photo p {{ font-size: 8pt; color: #666; margin: 2px 0; }}
    </style></head><body>
    <h1>{title}</h1>
    <div class="grid">"""

    for photo in photos:
        html += f"""<div class="photo">
            <img src="{photo['path']}">
            <p><b>{photo.get('room', '')}</b> — {photo.get('caption', '')}</p>
        </div>"""

    html += "</div></body></html>"

    HTML(string=html).write_pdf(output)
    print(f"Photo sheet: {output}")
```

## One-Command Full Report

```bash
# Generate complete ArchiScan deliverable package
python3 scripts/generate_full_report.py \
  --scan-data scan_results.json \
  --photos photos/ \
  --output deliverables/ \
  --formats pdf,dxf,csv,svg

# Output:
# deliverables/
# ├── rapport_archiscan.pdf    (full report)
# ├── plan_rdc.dxf             (annotated floor plan)
# ├── plan_rdc.svg             (web-viewable plan)
# ├── metres.csv               (quantities for estimation)
# └── planche_photos.pdf       (photo contact sheet)
```

## Tips

- WeasyPrint produces print-quality PDFs with CSS — perfect for architectural reports.
- DXF files open in AutoCAD, LibreCAD, FreeCAD, DraftSight.
- SVG plans can be embedded in web dashboards or shared via email.
- Use consistent layer naming in DXF for interoperability with CAD workflows.
- Include a scale bar and north arrow in plans (add to SVG/DXF generation).
- Always include raw data references (scan files, photo links) in the report appendix.
