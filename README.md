# Nakshatra PDF Generator

A separate local Streamlit application for 27 Tamil nakshatra articles and 37
PDF outputs. No AI service or API key is needed.

## Run

```powershell
cd D:\nakshtra
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8506
```

## Editor workflow

1. Load one Word/text master or paste all 27 articles in the rich-text editor.
   Put each nakshatra name on its own line before that article. The app checks
   for missing articles and duplicate headings and uses the canonical order in
   `asset/names.json`, regardless of paste order. Prefix material is ignored.
2. Optionally upload the front-cover picture. Zoom and movement apply only to
   this picture. Lord images, contact banner and back cover have no upload UI.
3. Select a named output in the sidebar to preview it. All 37 combinations are
   available: 27 individual, 9 consecutive groups of three, and one complete PDF.
   Preview edits update the master source paragraph and therefore every output
   containing that paragraph. The preview uses the same bytes as the export.
4. Auto refresh defaults off for responsive typing. Use REFRESH PREVIEW after
   editing. Switching output generates only that preview; it does not generate
   all 37 on every keystroke.
5. Use Select all, Clear all, Singles, Groups, Full, searchable selection or the
   individual tick boxes to choose downloads. Prepare selected downloads shows
   progress and a size/page report. One selection downloads a PDF; several
   download a ZIP containing only those selected PDFs.

The editor supports bold, paragraph/subheading formatting, colors, font sizes,
manual line breaks, alignment, selected-text links and direct PDF preview edits.
A paragraph crossing pages remains one source paragraph. Edits in one preview
are shared; they are not independent overrides for that output.

## Output rules

- Single: maximum 200,000 bytes. Groups of 3: maximum 400,000 bytes.
- All 27: maximum 1,500,000 bytes. Image compression adapts to the limit while
  text remains vector. If a limit cannot be met, the app reports the failure.
- Each selected star begins on a fresh content page with its fixed lord image
  and red centered heading. Content continues as needed inside the border.
- The fixed phone banner is the final content element. If necessary it receives
  a contact page. The fixed back cover is always the last page.
- The supplied artwork is used as the default cover. A front upload replaces
  that large cover artwork. The fixed back cover and phone banner never change.
- Optional link controls cover the front/banner, Android app, contact and email.
  PDF link hotspots follow the reference back-cover positions. Turning links
  off removes all link annotations.

## Runtime structure

```text
app.py                 Streamlit editor, 37 previews, selection, cache and ZIP UI
engine.py              canonical section parsing, layouts, limits, output catalog
render_support.py      Tamil shaping, image preparation, links and Unicode maps
text_engine.py         rich text cleanup, font validation and vector Story rendering
editor/index.html      local rich text + editable rendered PDF component
requirements.txt       Streamlit, PyMuPDF, fonttools, Pillow, tzdata
asset/names.json        canonical 27-star sequence
asset/lords/01..27.png  fixed lord images
asset/font/*.ttf        supplied complete Tamil fonts
asset/cover.jpg         default front artwork
asset/phone.jpg         fixed phone banner
asset/back.jpg          fixed back cover
```

Deploy with repository root `app.py` as the entry point and include all runtime
files above. Do not publish the source Word article, reference PDFs, generated
PDFs, temp files or local test files. Generated files remain in session memory
until downloaded. The ZIP includes Tamil names and numeric ordering prefixes.

Ashwini uses the supplied original image, replacing the initial reference-PDF extraction.
The alternate Mrigaseerisham image filename maps to canonical Mrigaseeridam.
Fonts are the supplied complete Sundaram-01 and Sundaram-06; text appearance
can differ from the reference PDF's original embedded fonts.

## Validation

Tests generate all 37 outputs from the supplied local Word article, verify
byte limits, every source character (Unicode normalized), source indices,
section ordering, fixed endings, links, selection-only ZIP contents, missing
and duplicate validation, and propagation of one master edit to all formats.
Run locally with `python -m unittest discover -s tests` (tests are development
files and are excluded from publishing). Browser checks cover the editor and
preview controls.

Download delivery uses a browser Blob, avoiding temporary media URLs. The default
text alignment is Justify; Left/Center/Right/Justify controls are available in the editor toolbar for individual paragraphs. Explicit paragraph alignment overrides the default.
