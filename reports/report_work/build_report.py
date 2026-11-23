from pathlib import Path
from copy import deepcopy
import hashlib, json, re, zipfile
from lxml import etree
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'reports' / 'report_work'
REF = WORK / 'reference.docx'
SOURCE = Path(r'C:\Users\ghrus\Downloads\PULSAR_Course_Project_Report.docx')
FINAL = ROOT / 'reports' / 'PULSAR_DFL_Final_Report.docx'
source = Document(SOURCE)
ref = Document(REF)
doc = Document(REF)
body = doc.element.body
sect_first = deepcopy(ref.sections[0]._sectPr)
sect_last = deepcopy(ref.sections[1]._sectPr)
for element in list(body):
    body.remove(element)
body.append(sect_last)

def append(el):
    body.insert(len(body)-1, el)
    return el

def text(p, value):
    rpr = deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    for e in list(p._p):
        if e.tag != qn('w:pPr'):
            p._p.remove(e)
    r = p.add_run(value)
    if rpr is not None:
        r._r.insert(0, rpr)
    return p

def para(value, role='body', before=False):
    prototypes={'body':94,'chapter':91,'section':149,'sub':151,'caption':225,'front':75}
    p=doc.add_paragraph()
    p._p.getparent().remove(p._p)
    p._p=deepcopy(ref.paragraphs[prototypes.get(role,94)]._p)
    p._element=p._p
    append(p._p)
    text(p,value)
    f=p.paragraph_format
    f.left_indent=Inches(0); f.right_indent=Inches(0)
    f.first_line_indent=Inches(0)
    f.page_break_before=before
    f.keep_with_next=role in ('chapter','section','sub')
    f.keep_together=False
    f.widow_control=True
    f.space_before=Pt(0 if role=='body' else 6)
    f.space_after=Pt(5 if role=='body' else 9)
    f.line_spacing=1.5 if role=='body' else 1.15
    p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY if role=='body' else (WD_ALIGN_PARAGRAPH.CENTER if role in ('chapter','front','caption') else WD_ALIGN_PARAGRAPH.LEFT)
    # Reuse the reference's paragraph geometry; apply real semantic heading styles.
    if role=='chapter': p.style=doc.styles['Heading 1']
    elif role=='section': p.style=doc.styles['Heading 2']
    elif role=='sub': p.style=doc.styles['Heading 3']
    elif role=='caption': p.style=doc.styles['Caption']
    else: p.style=doc.styles['Normal']
    for r in p.runs:
        r.font.name='Times New Roman'
        r.font.size=Pt(16 if role in ('chapter','front') else 12 if role!='caption' else 10)
        r.font.color.rgb=RGBColor(0,0,0)
        r.bold=role in ('chapter','section','sub','front')
        r.italic=role=='caption'
        r.underline=False
    return p

def src(*indices):
    for i in indices:
        para(source.paragraphs[i].text.strip().replace('`',''))

def table(headers, rows, widths=None, size=10.5):
    # Source-derived grid table with the reference's thin black cell borders.
    t=doc.add_table(rows=1,cols=len(headers))
    t._tbl.getparent().remove(t._tbl);append(t._tbl)
    t.autofit=False
    if widths is None: widths=[6.63/len(headers)]*len(headers)
    for i,w in enumerate(widths): t.columns[i].width=Inches(w)
    for cell,value in zip(t.rows[0].cells,headers): cell.text=str(value)
    for vals in rows:
        for cell,value in zip(t.add_row().cells,vals): cell.text=str(value)
    for ri,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr()
        keep=OxmlElement('w:cantSplit');trpr.append(keep)
        if ri==0:
            repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
        for ci,c in enumerate(row.cells):
            c.width=Inches(widths[ci])
            pr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for side in ('top','left','bottom','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'000000');borders.append(e)
            pr.append(borders)
            margins=OxmlElement('w:tcMar')
            for side in ('top','bottom','left','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'65');e.set(qn('w:type'),'dxa');margins.append(e)
            pr.append(margins)
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(2)
                p.paragraph_format.line_spacing=1.0
                for r in p.runs:
                    r.font.name='Times New Roman';r.font.size=Pt(size);r.bold=ri==0
    return t

def picture(path, caption, width=6.2, maxheight=5.9):
    path=Path(path)
    w,h=Image.open(path).size
    width=min(width,maxheight*w/h)
    p=para('',role='caption')
    p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.keep_with_next=True
    shape=p.add_run().add_picture(str(path),width=Inches(width))
    shape._inline.docPr.set('descr',caption)
    cap=para(caption,'caption')
    cap.paragraph_format.keep_with_next=False

def diagram(name, boxes, links, size=(1800,1000)):
    im=Image.new('RGB',size,'white');d=ImageDraw.Draw(im)
    fontpath=Path(r'C:\Windows\Fonts\times.ttf')
    font=ImageFont.truetype(str(fontpath),34)
    for x,y,w,h,label in boxes:
        d.rounded_rectangle((x,y,x+w,y+h),radius=10,fill='#f5f5f5',outline='black',width=3)
        lines=label.split('\n');ly=y+h/2-len(lines)*22
        for line in lines:
            d.text((x+w/2,ly),line,font=font,fill='black',anchor='mt');ly+=44
    for x1,y1,x2,y2 in links:
        d.line((x1,y1,x2,y2),fill='black',width=4)
        import math
        a=math.atan2(y2-y1,x2-x1)
        pts=[(x2,y2),(x2-19*math.cos(a-.45),y2-19*math.sin(a-.45)),(x2-19*math.cos(a+.45),y2-19*math.sin(a+.45))]
        d.polygon(pts,fill='black')
    out=WORK/(name+'.png');im.save(out);return out

# New figures are technical diagrams made from project facts, not borrowed figures.
arch=diagram('architecture',[
 (600,25,600,120,'React Admin and Doctor interface'),
 (600,215,600,120,'FastAPI authentication and services'),
 (45,440,480,120,'SQLite and SQLAlchemy\nRecords and experiment queue'),
 (660,440,480,120,'ResNet18 inference\nand Grad CAM'),
 (1270,440,480,120,'Protected images\nand PDF reports'),
 (45,710,480,120,'Separate training worker'),
 (660,710,480,120,'Shared training engine'),
 (1270,710,480,120,'Flower clients A B C')],
 [(900,145,900,215),(680,335,285,440),(900,335,900,440),(1130,335,1510,440),(285,560,285,710),(525,770,660,770),(1140,770,1270,770)],(1800,900))
fed=diagram('federated_workflow',[
 (500,20,800,130,'Coordinator global ResNet18 model'),
 (30,270,520,140,'Hospital A\nLocal partition and training'),
 (640,270,520,140,'Hospital B\nLocal partition and training'),
 (1250,270,520,140,'Hospital C\nLocal partition and training'),
 (500,555,800,135,'FedAvg or FedProx aggregation\nOptional Flower SecAgg plus'),
 (500,815,800,125,'Validation metrics and checkpoint')],
 [(650,150,290,270),(900,150,900,270),(1150,150,1510,270),(290,410,650,555),(900,410,900,555),(1510,410,1150,555),(900,690,900,815)],(1800,990))
appflow=diagram('application_workflow',[
 (100,40,700,120,'Login and role authorization'),
 (1000,40,700,120,'Admin account and research views'),
 (100,290,700,120,'Doctor selects an owned patient'),
 (1000,290,700,120,'Validate and protect PNG or JPEG'),
 (1000,540,700,120,'Strict ResNet18 and Grad CAM'),
 (100,540,700,120,'Persist analysis and doctor review'),
 (100,790,700,120,'Generate protected PDF report')],
 [(800,100,1000,100),(450,160,450,290),(800,350,1000,350),(1350,410,1350,540),(1000,600,800,600),(450,660,450,790)],(1800,960))

# Cover: copy the reference's actual paragraphs, typography, and VIT logo.
cover={
 1:'A Course Project Report',2:'on',
 3:'PULSAR\nDistributed Lung Cancer Image Classification Using Privacy Preserving Federated Learning',
 7:'Computer Science and Engineering',8:'Artificial Intelligence',
 14:'Lalit More (12411598)',15:'Ghrushnesh Patil (12411658)',
 16:'Saksham Moon (12414037)',17:'Pranav Panure (12414949)',
 22:'(ARTIFICIAL INTELLIGENCE)',23:"BANSILAL RAMNATH AGARWAL CHARITABLE TRUST'S"}
for i in [i for i in range(26) if i not in (0,6,9,13,20)]:
    el=deepcopy(ref.paragraphs[i]._p);append(el)
    from docx.text.paragraph import Paragraph
    p=Paragraph(el,doc._body)
    if i in cover: text(p,cover[i])
    if i==3:
        p.style=doc.styles['Title']
        for r in p.runs:
            r.font.color.rgb=RGBColor(0,0,0)
            r.underline=False
para('PUNE 411037',role='caption')
para('ACADEMIC YEAR 2026-27',role='caption')

# Certificate uses the reference's institutional heading and signature roles.
for i in [28,29,30,31]:
    el=deepcopy(ref.paragraphs[i]._p);append(el)
    p=Paragraph(el,doc._body)
    if i==28:
        p.paragraph_format.page_break_before=True
        text(p,"BANSILAL RAMNATH AGARWAL CHARITABLE TRUST'S")
    if i==29:text(p,'VISHWAKARMA INSTITUTE OF TECHNOLOGY')
    if i==31:text(p,'PUNE 411037')
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
logo=para('','caption')
logo.add_run().add_picture(str(WORK/'image1.jpeg'),width=Inches(1.05))
logo.paragraph_format.space_before=Pt(14)
logo.paragraph_format.space_after=Pt(14)
certificate_heading=para('CERTIFICATE','front')
for run in certificate_heading.runs:run.font.size=Pt(28)
cert=para(source.paragraphs[25].text)
cert.paragraph_format.space_before=Pt(25)
cert.paragraph_format.space_after=Pt(48)
signatures=table(['Project Guide','Head of Department'],[
 ['Prof. Jayshree Bedade','Prof. Dr. Nilesh P. Sable'],
 ['Computer Science and Engineering\nArtificial Intelligence','Computer Science and Engineering\nArtificial Intelligence']], [3.2,3.3],12)
for row in signatures.rows:
    for cell in row.cells:
        borders=cell._tc.get_or_add_tcPr().find(qn('w:tcBorders'))
        if borders is not None:
            for edge in borders:edge.set(qn('w:val'),'nil')
        for p in cell.paragraphs:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
para('Place  Pune')
para('Date  ____________________')

para('ACKNOWLEDGEMENT','front',True)
src(33,34,35,36,37)
for i in (38,39,40,41):
    p=para(source.paragraphs[i].text);p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;p.paragraph_format.space_after=Pt(2)

para('ABSTRACT','front',True)
src(44,45,46,47)

para('TABLE OF CONTENTS','front',True)
toc_rows=[
 ('','CHAPTER 1 INTRODUCTION','1'),('1.1','Overview of the Project','1'),('1.2','Problem Statement','1'),('1.3','Objectives','2'),('1.4','Scope of the Project','2'),
 ('','CHAPTER 2 LITERATURE SURVEY','3'),('2.1','Background and Related Concepts','3'),('2.2','Existing System and Its Limitations','4'),('2.3','Proposed System Overview','4'),('2.4','Research Gap and Motivation','4'),
 ('','CHAPTER 3 SYSTEM DESIGN','5'),('3.1','System Requirements','5'),('3.2','System Architecture','6'),('3.3','Module Description','7'),('3.4','Data Flow and Federated Workflow','10'),
 ('','CHAPTER 4 IMPLEMENTATION AND TESTING','11'),('4.1','Experimental Setup','11'),('4.2','Implementation Methodology','12'),('4.3','Evaluation Metrics','14'),('4.4','Results and Discussion','15'),('4.5','Testing and Validation','17'),('4.6','Screenshots','18'),
 ('','CHAPTER 5 CONCLUSION AND FUTURE SCOPE','24'),('5.1','Conclusion','24'),('5.2','Future Scope','25'),('','REFERENCES','26')]
toc=table(['Sr No','Title of Chapter or Contents','Page No'],toc_rows,[.55,5.25,.65],10)
for row in toc.rows:
    for c in row.cells:
        for p in c.paragraphs:
            p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(1)
for row in toc.rows[1:]:
    if not row.cells[0].text:
        for r in row.cells[1].paragraphs[0].runs:r.bold=True

# Section break preserves the source's two-section system and body page restart.
p=doc.add_paragraph();p._p.getparent().remove(p._p);append(p._p)
p._p.get_or_add_pPr().append(sect_first)
p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1
p.add_run().font.size=Pt(1)

page_log=[]
def page(number, heading, chapter=False):
    page_log.append({'body_page':number,'heading':heading})
    return para(heading,'chapter' if chapter else 'section',number!=1)

page(1,'CHAPTER 1  INTRODUCTION',True)
para('1.1 Overview of the Project','section')
para('PULSAR is a course-project research application for lung image classification and privacy-aware distributed training. It connects a doctor-facing image-analysis workflow, persistent patient records, and a learning pipeline that compares centralized and federated optimization. It is a local research prototype rather than a clinically approved diagnostic product.')
para('ResNet18 is the single active classifier, with a four-class output head. Centralized training, Federated Averaging (FedAvg), and Federated Proximal (FedProx) are training strategies using this common architecture. Three simulated hospitals perform client-specific training. Flower SecAgg+ and experimental Opacus DP-SGD address different aspects of update protection.')
src(57)
para('1.2 Problem Statement','section')
para('Medical institutions may hold image datasets that cannot be freely pooled because of privacy, governance, and operational constraints. Centralized training assumes pooled access; federated learning instead communicates model updates while keeping routine training-image processing local. Individual updates can still reveal information, so data locality alone does not establish privacy.')
para('PULSAR addresses this problem by implementing and evaluating centralized and federated image classification, exploring secure aggregation and differential privacy separately, and integrating controlled access to patient records. Model class probabilities and Grad-CAM must remain distinct from confirmed diagnosis, patient-level certainty, and doctor-entered observations.')

page(2,'1.3 Objectives')
para('The project aims to implement an integrated research prototype for lung image classification and controlled federated learning experiments. Its objectives are to:')
objectives=[
 'Validate one four-class ResNet18 architecture and a strict checkpoint metadata contract.',
 'Compare centralized, FedAvg, and FedProx training using a shared optimization and evaluation engine.',
 'Simulate three hospitals with reproducible non-IID partitions, real local optimization, and aggregation.',
 'Integrate Flower SecAgg+ and verify aggregate-only visibility at the documented coordinator boundary.',
 'Implement experimental Opacus DP-SGD with clipping, noise, and cumulative RDP accounting.',
 'Provide Grad-CAM visualizations and clearly communicate their interpretation limits.',
 'Develop authenticated Admin and Doctor workflows, patient ownership, protected files, and PDF reports.',
 'Persist experiment settings, round metrics, checkpoints, results, and failures.']
for i,value in enumerate(objectives,1):
    p=para(f'{i}. {value}');p.paragraph_format.line_spacing=1.15;p.paragraph_format.space_after=Pt(6)
para('1.4 Scope of the Project','section')
para('The scope includes the React application, FastAPI backend, SQLite persistence, protected raster-image inference, Grad-CAM, centralized and federated training, secure aggregation, and experimental DP-SGD. Clients run as three hospital processes on one local machine. This demonstrates training and protocol behavior, not independently administered multi-hospital deployment or protection against the shared-host administrator.')
src(81)
para('Clinical deployment, regulatory approval, validated DICOM processing, external validation, and production privacy governance remain outside the verified scope.')

page(3,'CHAPTER 2  LITERATURE SURVEY',True)
para('2.1 Background and Related Concepts','section')
para('2.1.1 Residual Learning and Medical Images','sub')
para('Residual networks learn transformations through blocks with shortcut connections. ResNet18 provides the common image-classification architecture used throughout PULSAR. The final fully connected layer produces four class scores. Model architecture and training strategy are separate choices: a centralized run, FedAvg run, and FedProx run can all use the same ResNet18 network. The project uses the torchvision implementation and its documented preprocessing conventions [2, 3].')
para('2.1.2 Federated Optimization','sub')
para('A coordinator distributes a global model to clients; each client optimizes on local data and returns an update. FedAvg combines client parameters with sample-count weighting. FedProx adds a local proximal penalty that discourages excessive movement from the global parameters when client data differs. These methods change optimization rather than the ResNet18 architecture.')
para('2.1.3 Privacy Mechanisms','sub')
para('Federated data locality does not automatically protect model updates. Secure aggregation lets a coordinator recover a permitted aggregate while limiting visibility of individual unmasked contributions under protocol assumptions. Differential privacy separately bounds an individual record contribution through a specified mechanism, clipping, noise, sampling, and composition accounting. Transport security and application authorization address further boundaries.')
para('2.1.4 Explainability and Evaluation','sub')
para('Grad-CAM highlights image regions associated with a model class score; it is not validated tumour localization or segmentation. Model performance also depends on class balance, source population, preprocessing, and independent splits. Accuracy is therefore accompanied by macro F1, balanced accuracy, per-class sensitivity and specificity, support counts, and explicit dataset limitations.')

page(4,'2.2 Existing System and Its Limitations')
para('Centralized training simplifies pooled optimization but assumes raw data can be transferred and governed centrally. Isolated local models lose opportunities for shared learning. Plain federated updates reduce routine raw-image transfer while leaving update disclosure concerns. A standalone training script also lacks authenticated records, protected file access, and experiment provenance.')
table(['Approach','Limitation'],[
 ['Centralized training','Requires pooled access and central governance of raw training data.'],
 ['Independent local models','Cannot directly benefit from the combined learning of other clients.'],
 ['Plain federated updates','Raw model updates can reveal information despite data locality.'],
 ['Model script without application','Does not provide patient ownership, protected files, or experiment provenance.']], [2,4.5])
para('2.3 Proposed System Overview','section')
para('PULSAR integrates role-specific React workspaces, validated FastAPI services, SQLite persistence, protected storage, strict ResNet18 inference, and a separate experiment worker. The coordinator communicates with three local clients for FedAvg/FedProx training. SecAgg+ masks permitted contributions before they cross the client-process boundary. Experimental DP-SGD separately clips and noises per-sample gradients with accounting.')
para('The doctor workflow connects patient selection, protected image upload, classification, Grad-CAM, observations, and PDF reporting. Research views retrieve persisted configurations, metrics, failures, and artifacts rather than invented dashboard values.')
para('2.4 Research Gap and Motivation','section')
para('The contribution is an integrated implementation and verification workflow, not a new neural-network architecture. A consistent model and dataset contract supports traceable comparisons, while application authorization connects experiments to a usable research interface. Data locality, aggregate visibility, and differential privacy are treated as distinct properties with separately documented limits.')

page(5,'CHAPTER 3  SYSTEM DESIGN',True)
para('3.1 System Requirements','section')
para('3.1.1 Hardware Requirements','sub')
table(['Component','Requirement or recorded configuration'],[
 ['Compute','A local computer supporting Python, Node.js, a browser, and concurrent client processes.'],
 ['Processor and accelerator','Recorded environment uses PyTorch CPU builds; no GPU requirement is claimed.'],
 ['Memory and storage','Capacity for model batches, environment, dataset, database, protected files, and checkpoints.'],
 ['Network','Loopback communication for the application and simulated hospital processes.']], [1.6,4.9])
para('3.1.2 Software Requirements','sub')
rows=[[c.text for c in r.cells] for r in source.tables[3].rows[1:]]
table(['Layer','Recorded technology','Purpose'],rows,[1.1,2.7,2.7],9.5)
para('Table 3.1  Hardware and software requirements','caption')
para('These versions describe the documented implementation snapshot. Dependency files and the frontend lockfile are the reproducibility inputs. Exact processor, RAM, and disk specifications are not established by the implementation records.')

page(6,'3.2 System Architecture')
src(138,139,140)
picture(arch,'Figure 3.1  PULSAR application and research architecture',6.4,4.0)
para('The inference path and experiment worker share model and manifest contracts, while their execution lifecycles remain separate. Patient records are not automatically added to training data. The model used for application analysis changes through explicit checkpoint selection rather than automatically after an experiment finishes.')

page(7,'3.3 Module Description')
para('3.3.1 Authentication and Account Management','sub');src(149,150)
para('3.3.2 Patient Records and Doctor Ownership','sub');src(151,152)
para('3.3.3 Persistence and Reporting','sub')
para('SQLite stores persistent users, sessions, patients, visits, analyses, reports, experiment records, and round metrics through SQLAlchemy. Alembic manages schema changes. Images, heatmaps, reports, and experiment artifacts are stored as protected files with corresponding records. A generated PDF represents a snapshot of the analysis and doctor review. Later edits do not silently rewrite an already generated report [1, 10, 11].')
para('The browser uses authorized API endpoints rather than direct database or filesystem access. A Doctor can retrieve owned patient resources; an Admin can manage doctor accounts and inspect aggregate experiment information, but cannot use Admin permissions to read patient scans.')

page(8,'3.3.4 Image Analysis and Explainability')
para('The upload module accepts PNG and JPEG with extension, MIME, content, size, and dimension checks. It decodes and re-encodes files before protected storage; the configured upload limit is 10 MiB. Authorized endpoints enforce ownership for images and derived artifacts.')
para('Inference loads approved.pt, version centralized-verification, through strict architecture, class-mapping, normalization, and preprocessing validation. Invalid checkpoints cause an explicit error rather than a silent substitution of legacy or random weights. Analyses persist class probabilities and model version/hash metadata.')
src(161)
para('3.3.5 Model and Preprocessing Contract','sub')
para('The active checkpoint records 64 by 64 RGB input, bilinear square resizing, ImageNet mean [0.485, 0.456, 0.406], and standard deviation [0.229, 0.224, 0.225]. It uses standard BatchNorm ResNet18 with 11,178,564 trainable parameters. The shared implementation also supports other configured resolutions and a GroupNorm variant for privacy-related experiments, without introducing another classifier family [1, 3].')
table(['Output index','Dataset label'],[['0','Adenocarcinoma'],['1','Large Cell Carcinoma'],['2','No Cancer'],['3','Squamous Cell Carcinoma']],[1.1,5.4])
para('The application does not use the retired clinical-tabular fusion or MobileNetV2 fallback paths. Doctor-entered history and observations remain record information, separate from image class probabilities.')

page(9,'3.3.6 Federated Learning and Experiment Tracking')
para('Centralized training, FedAvg, and FedProx use a shared ResNet18 training engine. Reproducible non-IID partitions can give Hospital A, B, and C different class distributions. In the recorded full-data seed/alpha setting, client training counts are 198, 233, and 75. Different seeds or Dirichlet alpha values can produce different partitions.')
para('FedAvg performs sample-weighted parameter averaging. FedProx adds a proximal local-loss term to limit drift from global parameters. Configurations and round metrics record how each experiment was actually trained.')
para('A separate worker claims experiments from a SQL-backed queue and persists status, metrics, checkpoints, failures, and artifacts. The documented setup uses one worker. Completed and invalidated historical records remain distinguishable, so unsuitable runs are not silently presented as valid evidence.')
para('3.3.7 Secure Aggregation and Differential Privacy','sub')
src(172,173)
para('Secure aggregation protects individual-update visibility under its protocol assumptions; DP-SGD addresses the influence of examples in its accounted mechanism. Neither replaces protected transport, storage controls, or access checks. The simulation excludes shared-host administrators and client collusion from its protection claim, and production privacy governance remains future work.')

page(10,'3.4 Data Flow and Federated Workflow')
picture(appflow,'Figure 3.2  Authorized application analysis workflow',6.2,3.4)
picture(fed,'Figure 3.3  Federated client training and global update workflow',6.0,3.5)
para('The coordinator communicates the global model to three simulated hospitals. Client sample counts determine ordinary FedAvg weighting. FedProx changes the local objective. SecAgg+ changes how permitted updates become visible to the coordinator; DP-SGD separately changes local gradient processing.')

page(11,'CHAPTER 4  IMPLEMENTATION AND TESTING',True)
para('4.1 Experimental Setup','section');src(182)
para('The selected inference checkpoint is approved.pt, version centralized-verification. It was trained from scratch for two outer epochs at 64 by 64 input using Adam, batch size 16, learning rate 0.001, seed 42, and four CPU threads. Model selection uses validation macro F1; the test set is evaluated after selection.')
para('4.1.1 Dataset Audit and Active Splits','sub')
para('The repaired workflow identified 1,565 source file copies, 838 unique file-byte hashes, and 727 unique decoded image contents. All 111 original test images had pixel-identical training copies. Active training therefore uses a reproducible grouped manifest, excluding duplicate copies while retaining original test groups for testing [1].')
table(['Class','Train','Validation','Test','Total'],[
 ['Adenocarcinoma',151,33,33,217],['Large Cell Carcinoma',130,28,29,187],['No Cancer',46,10,10,66],['Squamous Cell Carcinoma',179,39,39,257],['Total',506,110,111,727]], [2.75,.8,1,.8,.8])
para('Table 4.1  Repaired active manifest distribution','caption')
src(189)

page(12,'4.2 Implementation Methodology')
para('4.2.1 Dataset and Checkpoint Validation','sub');src(187,188)
para('The manifest links source paths, labels, hashes, groups, splits, and optional patient/study identifiers. Source hashes and split isolation are checked before training. A stored manifest digest links checkpoint provenance to the evaluated data boundary.')
para('4.2.2 Training and Model Selection','sub')
para('The shared engine validates configuration, seeds training components, constructs ResNet18, and creates training and validation loaders. It performs real optimizer steps and records loss, accuracy, macro F1, and duration. Early stopping and best-checkpoint selection use validation performance. The selected checkpoint records architecture, ordered labels, normalization, preprocessing, algorithm, configuration, and manifest provenance.')
para('The selected checkpoint uses BatchNorm; configured DP/secure experiments can use GroupNorm. Strict loading rejects incompatible weights and mappings. Model approval means research-checkpoint selection, not medical approval.')
para('4.2.3 Federated Local Objectives','sub')
para('For client k with n_k examples, FedAvg forms a sample-weighted global model: w_next = sum_k (n_k / sum_j n_j) w_k. FedProx adds (mu / 2) times the squared distance from the received global parameters to each local loss. This proximal term addresses local model drift under heterogeneous client data; it does not encrypt an update.')

page(13,'4.2.4 Secure Aggregation and Experimental DP SGD')
src(145,146)
para('The secure configuration registers three clients, requires at least two contributors, and uses a two-of-three reconstruction threshold. Protocol evidence records completed stages, responder counts, contributor counts, quantization configuration, duration, and serialized message sizes. Secret keys, raw reconstruction payloads, and masked vectors are not exposed as public audit artifacts [1, 4, 5].')
para('The cryptographic adapter uses ChaCha20 and HKDF to expand domain-separated protocol material into masks. Unmasked arrays are cleared in the client process before a reply crosses the process boundary. Public counts, timing, global model parameters, and aggregate validation results remain visible [8, 9].')
para('Opacus DP-SGD applies per-sample gradient clipping and Gaussian noise with cumulative RDP accounting. A recorded two-round full-data experiment used noise multiplier 1.1, clipping norm 1.0, and delta 0.00001. Its per-client epsilon values are mechanism-specific; they are not a patient-level budget or a budget for the whole application [1, 6, 7].')
para('Private partition construction, patient-level composition, held-out evaluations, application records, and cross-experiment releases are outside that accountant scope. The full-data DP run used plaintext aggregation. Combined secure FedProx with DP was tested separately on a small repository-data subset as integration evidence.')

page(14,'4.3 Evaluation Metrics')
para('The project evaluates multiclass classification and operational behavior separately. Accuracy alone does not show how performance differs between classes; balanced accuracy, macro F1, and per-class sensitivity are therefore reported with the test support counts.')
table(['Metric','Definition and interpretation'],[
 ['Accuracy','Correct predictions divided by total evaluated images.'],
 ['Precision','True positives divided by true positives plus false positives, for a selected class.'],
 ['Sensitivity or recall','True positives divided by true positives plus false negatives.'],
 ['Specificity','True negatives divided by true negatives plus false positives, one class versus the rest.'],
 ['F1 score','2 times precision times recall divided by precision plus recall.'],
 ['Macro F1','Unweighted average of class F1 scores; each class contributes equally.'],
 ['Balanced accuracy','Average class recall, reducing dominance by larger classes.'],
 ['ROC AUC','One-versus-rest ranking measure over decision thresholds where defined.'],
 ['Communication','Logical tensor bytes for plaintext runs; serialized protocol-message bytes for secure runs.']], [1.65,4.85])
para('Table 4.2  Evaluation metrics and measurement scope','caption')
para('A class probability is a softmax model output, not a calibrated estimate that a patient has cancer. Timing measured in a batch evaluation is also different from full API latency with Grad-CAM and database work. Communication totals with different scopes or round counts cannot establish a controlled protocol overhead comparison.')
para('All numerical comparisons in this report refer to stored project measurements. These records support local research verification; patient-independent generalization, external clinical performance, calibration, and confidence intervals remain unestablished.')

page(15,'4.4 Results and Discussion')
para('4.4.1 Selected Inference Model','sub')
para('The selected centralized-verification checkpoint correctly classified 84 of 111 held-out images, giving 75.68% accuracy. The saved evaluation reports balanced accuracy 74.52%, macro precision 77.84%, macro recall 74.52%, macro F1 73.35%, and macro one-versus-rest ROC-AUC 0.9406 [1].')
table(['Class','Sensitivity','Specificity','Support'],[
 ['Adenocarcinoma','81.82%','84.62%',33],['Large Cell Carcinoma','41.38%','98.78%',29],['No Cancer','80.00%','97.03%',10],['Squamous Cell Carcinoma','94.87%','84.72%',39]], [2.7,1.25,1.25,.9])
para('Table 4.3  Per class performance of the selected checkpoint','caption')
table(['Actual versus predicted','Adeno','Large Cell','No Cancer','Squamous'],[
 ['Adenocarcinoma',27,1,2,3],['Large Cell Carcinoma',10,12,0,7],['No Cancer',1,0,8,1],['Squamous Cell Carcinoma',1,0,1,37]], [2.65,.85,1.05,1.05,1.05])
para('Table 4.4  Confusion matrix with true classes as rows','caption')
para('The overall score conceals a weaker Large Cell Carcinoma recall: 12 of its 29 images were correctly identified, while ten were classified as Adenocarcinoma and seven as Squamous Cell Carcinoma. No Cancer has only ten test images. These class-specific limits are more informative than treating the aggregate accuracy as individual clinical certainty.')
para('The repaired split prevents audited exact duplicate overlap, but trusted patient or study identifiers are absent. Related slices or unrecognized near duplicates may remain. These results therefore apply to the documented image-group split and do not prove external or patient-independent performance.')

page(16,'4.4.2 Experiment Comparison and Interpretation')
table(['Recorded experiment','Rounds','Normalization','Accuracy','Macro F1'],[
 ['Centralized verification',2,'BatchNorm','75.68%','73.35%'],
 ['Plaintext FedAvg',2,'BatchNorm','48.65%','38.94%'],
 ['Plaintext FedProx',2,'BatchNorm','46.85%','39.65%'],
 ['FedAvg with experimental DP',2,'GroupNorm','32.43%','12.50%'],
 ['FedAvg with SecAgg plus',1,'GroupNorm','36.04%','14.56%']], [2.4,.6,1.15,.95,.95])
para('Table 4.5  Recorded verification experiments on the 111 image test boundary','caption')
table(['Run','Duration','Communication bytes','Measurement scope'],[
 ['Centralized','20.362 s','0','No federated transfer'],
 ['FedAvg','27.674 s','537033792','Logical model tensor payload'],
 ['FedProx','29.289 s','537033792','Logical model tensor payload'],
 ['DP FedAvg','81.404 s','536571072','Logical model tensor payload'],
 ['Secure FedAvg','42.098 s','402499977','Serialized Flower messages']], [1.1,.9,1.4,3.1])
para('Table 4.6  Recorded execution duration and communication','caption')
para('These are short verification runs with different optimizers, normalization choices, budgets, and privacy settings. The centralized, plain federated, and DP runs used Adam; the secure run used SGD and only one round. Their accuracy differences do not isolate the effect of secure aggregation or DP noise. The 36.04% secure result is a separate experiment with DP disabled and did not replace the 75.68% application checkpoint.')
para('Durations are specific to the recorded machine and include final evaluation. Secure communication includes serialized messages in both directions, while plaintext totals count logical model tensors. Different measurement scopes and round counts prevent interpreting these totals as a direct privacy-overhead comparison.')

page(17,'4.5 Testing and Validation')
para('Recorded verification comprises 41 passing backend tests in one full run and one later passing encrypted-share tamper test, for 42 distinct tests across separate runs. Six browser tests, the frontend build, ESLint, and pip check also passed in the documented snapshot. These are local software checks, not clinical validation or security certification.')
table(['Verification area','Recorded evidence','Boundary'],[
 ['Backend','41 passed in one full run and one later tamper test passed','42 distinct tests across separate recorded runs'],
 ['Browser','Six passing end to end tests','Local workflows, mobile layout, downloads, and error handling'],
 ['Frontend','Production build and ESLint passed','Build and static verification'],
 ['Dependencies','pip check passed','No broken requirements in the inspected environment'],
 ['Dataset','Repeat manifest digest matches; no exact cross split overlap','Does not establish patient independence'],
 ['Privacy protocol','Reconstruction, dropout, mask, tamper, replay, and DP checks','Scoped protocol and integration evidence']], [1.15,2.65,2.7])
para('Table 4.7  Recorded software and dataset verification','caption')
para('Backend coverage includes authentication, roles, disabled sessions, ownership isolation, patient workflows, upload validation, protected resources, strict checkpoints, saved analyses, Grad-CAM, PDF content, dataset integrity, and worker execution. Protocol tests check weighted reconstruction, masked payload visibility, fresh masks, seed/domain separation, dropout, minimum participants, replay or malformed messages, and corrupted encrypted shares.')
para('Worker tests run secure FedAvg and secure FedProx with DP on a real repository-image subset and persist database results and checkpoints. Browser tests cover role navigation, forms, API workflows, protected downloads, mobile layout, and loading/error/retry behavior. Test databases, known protocol vectors, and explicitly untrained fixture weights are isolated from research benchmark evidence. The recorded suite was not rerun to prepare this report.')

page(18,'4.6 Screenshots')
para('4.6.1 Authentication Interface','sub')
picture(ROOT/'docs/screens/login-desktop.png','Figure 4.1  PULSAR login capture showing credential validation feedback',6.5,5.0)
para('The login screen is the entry point for Admin and Doctor sessions. This existing verification capture shows an invalid-credentials or inactive-account message, demonstrating the visible error state. Backend authentication establishes revocable sessions and determines the workspace. Patients are records managed by doctors and do not have login accounts.')
para('Authentication, role enforcement, and disabled-account handling are server responsibilities. The interface does not replace backend ownership checks, and a hidden navigation item is not treated as an access-control mechanism.')

page(19,'4.6.2 Admin Workspace')
picture(ROOT/'docs/screens/admin-desktop.png','Figure 4.2  PULSAR Admin overview capture with loading placeholders',6.5,5.8)
src(208)
para('This capture shows the overview layout and navigation while summary cards and recent experiments are loading. The placeholders are interface states, not measured values. Populated experiment evidence appears in the federated and comparison captures. None of these images is a fresh benchmark or evidence of clinical deployment.')

page(20,'4.6.3 Doctor Workspace')
picture(ROOT/'docs/screens/doctor-desktop.png','Figure 4.3  PULSAR Doctor patient workspace using a browser test record',6.5,5.6)
src(209,212)

page(21,'4.6.4 Image Analysis and Grad CAM')
picture(ROOT/'docs/screens/doctor-analysis.png','Figure 4.4  Existing image analysis and Grad CAM capture using a browser test record',5.1,6.5)
para('This capture uses a Browser Test Patient record. It shows image class probabilities, model metadata, a Grad-CAM overlay, and doctor-entered review fields. The displayed probability belongs to this example analysis; it is not the model test accuracy or a validated patient risk estimate. The heatmap indicates class-associated model regions rather than a confirmed lesion boundary.')

page(22,'4.6.5 Federated Experiment Workspace')
picture(ROOT/'docs/screens/federated-desktop.png','Figure 4.5  Existing PULSAR federated experiment dashboard capture',5.8,6.4)
src(216)
para('Each experiment must be interpreted using its own configuration, normalization, rounds, aggregation mode, and DP setting. Secure aggregation and differential privacy are separate mechanisms; a secure run must not be relabelled DP-enabled when noise was disabled.')

page(23,'4.6.6 Model Comparison and Protected Reports')
picture(ROOT/'docs/screens/comparison-desktop.png','Figure 4.6  Existing PULSAR model comparison capture',5.4,5.9)
para('The comparison workspace presents stored experiment results and their evidence boundaries. A selected model remains explicit rather than being changed by a chart ranking. Doctors can also generate protected PDF snapshots containing the uploaded image, analysis, model metadata, heatmap, and their observations. Record ownership is checked for both generation and download.')

page(24,'CHAPTER 5  CONCLUSION AND FUTURE SCOPE',True)
para('5.1 Conclusion','section');src(231,232,233,234,235)

page(25,'5.2 Future Scope')
src(237,238,239,240,241)

page(26,'REFERENCES',True)
for i in range(250,262):
    p=para(source.paragraphs[i].text.replace('`',''))
    p.alignment=WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing=1.1
    p.paragraph_format.space_after=Pt(8)
    for r in p.runs:r.font.size=Pt(10.5)

# Preserve both original section geometries, borders, numbering, and footer links.
settings=doc.settings.element
update=settings.find(qn('w:updateFields'))
if update is None:update=OxmlElement('w:updateFields');settings.append(update)
update.set(qn('w:val'),'true')
doc.core_properties.title='PULSAR Distributed Lung Cancer Image Classification Using Privacy Preserving Federated Learning'
doc.core_properties.subject='Distributed and Federated Learning Course Project Report'
doc.core_properties.author='Lalit More; Ghrushnesh Patil; Saksham Moon; Pranav Panure'
doc.core_properties.last_modified_by='PULSAR Project Team'

intermediate=WORK/'assembled.docx'
doc.save(intermediate)

# Overlay only authorized content parts and new image relationships. Untouched
# styles, theme, numbering, footnotes, headers, footers and custom XML remain exact.
editable={'word/document.xml','word/_rels/document.xml.rels','word/settings.xml','docProps/core.xml'}
with zipfile.ZipFile(REF) as original,zipfile.ZipFile(intermediate) as changed,zipfile.ZipFile(FINAL,'w',zipfile.ZIP_DEFLATED) as out:
    originals=set(original.namelist())
    for info in original.infolist():
        out.writestr(info,changed.read(info.filename) if info.filename in editable else original.read(info.filename))
    for info in changed.infolist():
        if info.filename not in originals:
            out.writestr(info,changed.read(info.filename))

with zipfile.ZipFile(REF) as a,zipfile.ZipFile(FINAL) as b:
    unchanged=[n for n in a.namelist() if n not in editable]
    failures=[n for n in unchanged if a.read(n)!=b.read(n)]
    assert not failures,failures
assert hashlib.sha256(REF.read_bytes()).hexdigest()=='d74a14e56c016bc72de825520141721028f496bbc8d4e99eeb24cb305225b2af'
final_doc=Document(FINAL)
alltext='\n'.join(p.text for p in final_doc.paragraphs)+'\n'+'\n'.join(c.text for t in final_doc.tables for r in t.rows for c in r.cells)
for stale in ['Disha Gupta','Meetal Gaikwad','Anuj Gardi','Harshal Ramteke','GraphSAGE','Bio_ClinicalBERT','99.30%','INSERT PROJECT']:
    assert stale not in alltext,stale
(WORK/'page_plan.json').write_text(json.dumps(page_log,indent=2))
(WORK/'final_text.txt').write_text(alltext,encoding='utf-8')
print(json.dumps({'output':str(FINAL),'paragraphs':len(final_doc.paragraphs),'tables':len(final_doc.tables),'figures':len(final_doc.inline_shapes),'preserve_only_parts_verified':len(unchanged),'body_pages_planned':len(page_log),'words':len(alltext.split())},indent=2))
