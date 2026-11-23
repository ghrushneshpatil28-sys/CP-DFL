# Reference contract for the PULSAR course project report

Reference retained at `F:\DFL-CP\reports\report_work\reference.docx`; original supplied at `D:\COLLEGE\SEM-5\DFL\Harshal\DFL REPORT FINAL.docx`.
SHA256 `d74a14e56c016bc72de825520141721028f496bbc8d4e99eeb24cb305225b2af`.
Reference render: `reference-render/`, 32 pages, reviewed in full. Source has five front-matter pages, an unwanted blank page, and 26 numbered body pages. Two sections.

## Page system

Both sections use Letter portrait, 12240 by 15840 twips, left margin 1440, top 1077, header distance 0, footer distance 283. First section right/bottom 1259; second section right/bottom 1253. Keep source page borders at 24 points from page edge, single 0.5 point. Keep section header/footer relationships and restart Arabic body numbering at one. First section has empty header/footer. Second footer contains PAGE fields. Omit the source's accidental blank page. Body length may change to accommodate replacement content; planned 26 body pages and five front-matter pages, subject to render review.

## Typography and reusable components

Default Times New Roman 12 point. Source body role is document paragraph 94: justified, 1.5 line spacing, no first-line indent. Chapter role paragraph 91: centered 16 point bold. Subsection role paragraph 149: left aligned bold 12 point. Subheading role paragraph 151: bold 12 point. Caption role paragraph 225: centered italic 10 point. Source cover paragraphs 0 through 25 provide centered title, degree, institute, team, guide, and logo arrangement, with 16/18 point typography and red cover accents. Use black Word Title for the replacement project title. Repair spelling and malformed quote characters. Keep the actual institutional logo relation; remove all unrelated project figures.

Use real Heading 1 through Heading 3 styles with source-derived direct formatting and no auto-numbering; chapter numbering is explicit. New tables follow source thin black grid, white body, bold header, compact line spacing. Widen content columns relative to numeric columns. Rows must not split; header rows repeat. Table font 9.5 to 12 points according to density, preserving legibility. New content can clone these paragraph/table patterns. No generic design preset is authorized.

## Content flow and edit slots

All original project-specific body content is replaceable. User explicitly confirmed DFL REPORT FINAL as format and PULSAR Course Project Report as content and team-name authority.

- Cover document paragraphs 0 to 27: replace title, four names/PRNs, correct department spelling, academic year 2026 27; preserve institute/guide/logo roles.
- Certificate paragraphs 28 to 48: preserve institution/title/signature roles; replace certificate content using PULSAR and correct team, course and academic year. No actual signatures are added.
- Acknowledgement paragraphs 49 to 74: PULSAR acknowledgements and team names.
- Abstract paragraphs 75 to 86: PULSAR scope, models, measured result, limitations.
- Contents paragraph 87 and table 0: replace every row and page number to match final chapters.
- Body section starts at paragraph 90 sectPr. Chapters 1 through 5 and references: full replacement with PULSAR subject matter, requirements, architecture, modules, dataflow, methods, results, tests, screenshots, conclusions, future work and references.
- Body illustrations: original non-PULSAR diagrams/screenshots are removed from visible content. Add three factual project architecture/workflow diagrams and six existing PULSAR screenshots from `docs/screens/`. Captions identify captured test/example content and distinguish model probabilities from evaluation accuracy.
- Source names Disha Gupta, Meetal Gaikwad, Anuj Gardi, Harshal Ramteke and the reference's IoT/BERT/GraphSAGE content must not survive in visible document content.

## Package preservation

Baseline inventory and SHA256 for every package part are in `reference_parts.json`. Only `word/document.xml`, `word/_rels/document.xml.rels`, `word/settings.xml`, and `docProps/core.xml` are editable; additional image parts are permitted. Update the title, subject, author and last-editor metadata to the PULSAR project and team, consistent with the user's request to correct names. Preserve every other existing part byte for byte, including styles, numbering, themes, footnotes/endnotes, headers, footers, custom XML, original media assets and other package metadata. Old unused media can remain in the ZIP but cannot be referenced by the replacement content. No content controls or document-body fields were found. Footer PAGE fields are retained. Set updateFields in settings; no LibreOffice round-trip save of the DOCX is allowed.

## Verification gates

Render all final pages with the packaged render_docx.py in an isolated container and inspect every page. Match source page geometry, serif typography, institutional front matter, borders and body footer. Check cover capacity, no isolated headings, table boundaries, full image/caption containment, no unwanted blank pages, correct contents page numbers. Compare source/final render and section/style evidence. Check all preserve-only package parts for byte equality; reference hashes must remain unchanged. Scan all visible text, including tables, for stale project content and incorrect names. Source evidence comes from the supplied PULSAR report, the current complete README, approved metadata/test JSON, verification summary and existing screenshots. Do not substitute the obsolete initial README findings for the repaired project's current state.
