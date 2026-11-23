import { useEffect, useRef, useState } from 'react'
import { motion as Motion, MotionConfig } from 'framer-motion'
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BarChart3, CalendarClock, Check, ChevronLeft, ChevronRight, CircleHelp, FileText, FlaskConical, Grid2X2, HeartPulse, Hospital, Layers3, LogOut, Menu, Plus, Search, ShieldCheck, Sparkles, Stethoscope, Upload, Users, X } from 'lucide-react'
import { api, navigate } from './api'
import { useResource } from './useResource'

const doctorNav = [['overview', 'Overview', Grid2X2], ['patients', 'Patient directory', Users], ['analysis', 'Image analysis', Activity], ['history', 'Analysis history', Layers3], ['reports', 'Reports', FileText], ['followups', 'Follow-up records', CalendarClock], ['profile', 'Doctor profile', Stethoscope]]
const adminNav = [['overview', 'Overview', Grid2X2], ['doctors', 'Doctor management', Stethoscope], ['federated', 'Federated learning', Hospital], ['comparison', 'Model comparison', BarChart3], ['privacy', 'Privacy & security', ShieldCheck], ['audit', 'Audit logs', FileText], ['settings', 'System settings', FlaskConical]]
const percent = value => value == null ? '—' : `${(value * 100).toFixed(1)}%`
const date = value => value ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: value.includes('T') ? 'short' : undefined }) : 'Not scheduled'
const title = value => value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase())

function Status({ value }) { return <span className={`status ${['completed', 'active', 'validated'].includes(value) ? 'good' : value === 'failed' ? 'bad' : ''}`}><i />{value}</span> }
function Empty({ title: heading = 'A clear space for your next step', text, action }) { return <div className="empty"><Layers3 size={32} /><h3>{heading}</h3><p>{text}</p>{action}</div> }
function Notice({ children }) { return <div className="notice"><CircleHelp size={18} /><span>{children || 'Research decision support, not a confirmed medical diagnosis. Review every AI output with clinical context.'}</span></div> }
function ErrorBox({ error, retry }) { return error ? <div className="error" role="alert">{error}{retry && <button className="text-button" onClick={retry}>Try again</button>}</div> : null }
function Resource({ resource, children }) {
  if (resource.error) return <ErrorBox error={resource.error} retry={resource.reload} />
  if (resource.loading) return <div className="skeleton" role="status" aria-label="Loading"><div /><div /><div /></div>
  return children(resource.data)
}
function Field({ label, name, type = 'text', value, required, options, wide, ...props }) {
  return <label className={`field ${wide ? 'wide' : ''}`}><span>{label}{required ? ' *' : ''}</span>{options ? <select aria-label={label} name={name} defaultValue={value} required={required} {...props}>{options.map(option => <option key={option} value={option}>{option || 'Select…'}</option>)}</select> : type === 'textarea' ? <textarea aria-label={label} name={name} defaultValue={value || ''} rows={3} required={required} {...props} /> : <input aria-label={label} name={name} type={type} defaultValue={value || ''} required={required} {...props} />}</label>
}
function Submit({ busy, children = 'Save changes' }) { return <button className="button primary" disabled={busy}>{busy ? 'Working…' : children}<ArrowRight size={17} /></button> }
function Brand() { return <a href="#/overview" className="brand"><div className="brand-icon"><Activity /></div><div>PULSAR<span>FEDERATED RESEARCH</span></div></a> }

function Dialog({ onClose, children }) {
  const ref = useRef(null)
  const close = useRef(onClose)
  useEffect(() => { close.current = onClose }, [onClose])
  useEffect(() => {
    const previous = document.activeElement
    ref.current.querySelector('button, input')?.focus()
    const keydown = event => {
      if (event.key === 'Escape') close.current()
      if (event.key !== 'Tab') return
      const items = [...ref.current.querySelectorAll('button, input, select, textarea, a[href]')].filter(item => !item.disabled)
      if (event.shiftKey && document.activeElement === items[0]) { event.preventDefault(); items.at(-1)?.focus() }
      if (!event.shiftKey && document.activeElement === items.at(-1)) { event.preventDefault(); items[0]?.focus() }
    }
    document.addEventListener('keydown', keydown)
    return () => { document.removeEventListener('keydown', keydown); previous?.focus() }
  }, [])
  return <div className="modal-backdrop"><section ref={ref} className="modal card" role="dialog" aria-modal="true" aria-labelledby="doctor-dialog">{children}</section></div>
}

function Login({ onLogin }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const setup = useResource('/setup/status')
  const firstRun = setup.data?.required && setup.data?.enabled
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const body = Object.fromEntries(new FormData(event.currentTarget))
      if (firstRun) {
        if (body.password !== body.confirm_password) throw new Error('Passwords do not match.')
        delete body.confirm_password
        body.setup_token = setup.data.setup_token
      }
      const data = await api(firstRun ? '/setup/admin' : '/auth/login', { method: 'POST', body })
      onLogin(data.user)
    }
    catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  return <div className="login"><section className="login-story"><Brand /><span className="eyebrow light">DISTRIBUTED INTELLIGENCE. CONNECTED CARE.</span><h1>One shared<br />purpose.<br /><em>Three perspectives.</em></h1><p>A research workspace connecting lung image analysis, doctor-led records, and federated learning.</p><div className="orbit-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-center"><HeartPulse size={76} /></div><span className="orbit-tag one"><Hospital size={17} /> Hospital A</span><span className="orbit-tag two"><Hospital size={17} /> Hospital B</span><span className="orbit-tag three"><Hospital size={17} /> Hospital C</span></div><div className="story-footer"><span>RESNET18 EXCLUSIVELY</span><span>RESEARCH / 01</span></div></section><section className="login-form"><div className="login-top"><span className="pill">RESEARCH ACCESS</span><ShieldCheck size={20} /></div><div><span className="eyebrow">YOUR WORKSPACE IS READY</span><h2>{firstRun ? <>Start your<br />workspace.</> : <>Welcome<br />back.</>}</h2><p>{firstRun ? "Create the first Admin account. Choose your own password; there are no default credentials." : "Sign in with your Admin or Doctor account."}</p><form onSubmit={submit}>{firstRun && <Field label="Admin full name" name="name" required minLength={2} maxLength={160} autoComplete="name" />}<Field label="Email address" name="email" type="email" required autoComplete="username" /><Field label="Password" name="password" type="password" required autoComplete={firstRun ? "new-password" : "current-password"} minLength={firstRun ? 12 : 1} maxLength={128} />{firstRun && <Field label="Confirm password" name="confirm_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" />}<ErrorBox error={error} /><ErrorBox error={setup.error} retry={setup.reload} />{setup.data?.required && !setup.data.enabled && <Notice>No administrator exists yet. Launch START.cmd to enable local first-time setup, or use the Admin bootstrap command in README.md.</Notice>}<Submit busy={busy || setup.loading || !!setup.error}>{firstRun ? "Create Admin and enter" : "Enter workspace"}</Submit></form><p className="small">Accounts are provisioned by your administrator. Patients are records managed by doctors.</p></div><Notice /></section></div>
}

function useRoute() {
  const [route, setRoute] = useState(window.location.hash.slice(2) || 'overview')
  useEffect(() => { const update = () => setRoute(window.location.hash.slice(2) || 'overview'); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update) }, [])
  return route.split('/')
}

export default function App() {
  const [auth, setAuth] = useState({ ready: false, user: null })
  const [page, id] = useRoute()
  const [mobile, setMobile] = useState(false)
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 760px)').matches)
  useEffect(() => { const media = window.matchMedia('(max-width: 760px)'); const changed = () => setNarrow(media.matches); media.addEventListener('change', changed); return () => media.removeEventListener('change', changed) }, [])
  useEffect(() => {
    let active = true
    api('/auth/me').then(data => { if (active) setAuth({ ready: true, user: data.user }) }).catch(() => { if (active) setAuth({ ready: true, user: null }) })
    const expired = () => setAuth({ ready: true, user: null })
    window.addEventListener('session-expired', expired)
    return () => { active = false; window.removeEventListener('session-expired', expired) }
  }, [])
  if (!auth.ready) return <div className="boot"><Activity size={42} /><p>Opening research workspace…</p></div>
  if (!auth.user) return <Login onLogin={user => { setAuth({ ready: true, user }); navigate('overview') }} />
  const user = auth.user
  const navigation = user.role === 'Admin' ? adminNav : doctorNav
  const allowed = [...navigation.map(row => row[0]), ...(user.role === 'Admin' ? ['experiment'] : ['patient', 'add-patient'])]
  const label = navigation.find(row => row[0] === page)?.[1] || (page === 'patient' ? 'Patient workspace' : page === 'experiment' ? 'Experiment details' : 'Add patient')
  async function logout() { try { await api('/auth/logout', { method: 'POST' }); setAuth({ ready: true, user: null }) } catch (error) { window.alert(error.message) } }
  function content() {
    if (!allowed.includes(page)) return <Empty title="This page is outside your workspace" text="Choose a page from your navigation." />
    if (page === 'overview') return <Overview user={user} />
    if (page === 'doctors') return <Doctors />
    if (page === 'federated') return <Federated />
    if (page === 'experiment') return <ExperimentDetail id={id} />
    if (page === 'comparison') return <Comparison />
    if (page === 'privacy') return <Privacy />
    if (page === 'audit') return <Audit />
    if (page === 'settings') return <Settings />
    if (page === 'add-patient') return <PatientForm />
    if (page === 'patient') return <PatientProfile key={id} id={id} />
    if (page === 'profile') return <DoctorProfile user={user} onSave={updated => setAuth({ ready: true, user: updated })} />
    if (page === 'history' || page === 'reports') return <Records type={page} />
    return <PatientDirectory mode={page} />
  }
  return <MotionConfig reducedMotion="user"><div className="app-shell"><a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById("main-content").focus() }}>Skip to main content</a><aside inert={narrow && !mobile} className={`sidebar ${mobile ? 'open' : ''}`}><Brand /><div className="workspace-label">{user.role.toUpperCase()} WORKSPACE <span>01</span></div><nav aria-label="Main navigation">{navigation.map(([key, text, Icon]) => <a key={key} href={`#/${key}`} className={page === key || (key === 'patients' && ['patient', 'add-patient'].includes(page)) ? 'active' : ''} onClick={() => setMobile(false)}><Icon size={19} />{text}<ArrowUpRight size={14} /></a>)}</nav><div className="sidebar-note"><FlaskConical /><strong>Built for inquiry.</strong><p>ResNet18. Real experiments.<br />Transparent limitations.</p><span className="pill">RESEARCH USE ONLY</span></div><div className="user-block"><span className="avatar">{user.name.slice(0, 2).toUpperCase()}</span><div><strong>{user.name}</strong><small>{user.role}</small></div><button aria-label="Log out" onClick={logout}><LogOut size={18} /></button></div></aside><div className="main-shell"><header className="topbar"><button className="mobile-toggle" aria-label="Toggle navigation" onClick={() => setMobile(!mobile)}><Menu /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{label}</strong></div><div className="topbar-right"><span className="live-dot" /> RESEARCH ENVIRONMENT <span className="divider" /> <span className="avatar small-avatar">{user.role === 'Admin' ? 'AD' : 'DR'}</span></div></header><main id="main-content" tabIndex={-1}><div className="page-heading"><div><span className="eyebrow">PULSAR / {user.role.toUpperCase()} CONSOLE</span><h1>{label}<span className="heading-dot">.</span></h1></div><span className="date-chip">{new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span></div><Motion.div key={`${page}/${id || ''}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .22 }}>{content()}</Motion.div><footer className="page-footer"><span>PULSAR / Distributed Lung Cancer Diagnosis Using Privacy-Preserving Federated Learning</span><span>Experimental research application</span></footer></main></div></div></MotionConfig>
}

function Overview({ user }) {
  const stats = useResource('/dashboard')
  const activity = useResource(user.role === 'Admin' ? '/admin/federated/experiments' : '/patients?page_size=4')
  const admin = user.role === 'Admin'
  return <><div className="bento"><section className="hero-card"><div><span className="eyebrow light">{admin ? 'THE BIG PICTURE' : 'DOCTOR-LED. RESEARCH-INFORMED.'}</span><h2>{admin ? 'Intelligence grows\nwhen we connect.' : 'Every patient.\nA fuller perspective.'}</h2><p>{admin ? 'Coordinate three hospitals, compare learning strategies, and inspect the evidence behind every round.' : 'Bring clinical history, medical imaging, and explainable AI into one focused workspace.'}</p><button className="button lime" onClick={() => navigate(admin ? 'federated' : 'patients')}>{admin ? 'Open research lab' : 'Open patient directory'}<ArrowUpRight size={18} /></button></div><div className="hero-art" aria-hidden="true"><div className="art-ring"><Activity size={70} /></div><span className="art-label">{admin ? 'A + B + C' : 'RESNET18'}</span><span className="art-star">✳</span></div></section><section className="card manifesto"><span className="eyebrow">RESEARCH PRINCIPLE / 01</span><ShieldCheck size={35} /><h3>Trust begins<br />with evidence.</h3><p>Federated learning alone does not guarantee privacy. Inspect implemented protections and their limitations.</p><a href={admin ? '#/privacy' : '#/analysis'} className="text-link">{admin ? 'Explore privacy status' : 'Review an image'}<ArrowUpRight size={16} /></a></section></div><Resource resource={stats}>{data => <div className="metric-grid">{Object.entries(data).map(([key, value], index) => <div className={`metric-card color-${index % 4}`} key={key}><span>{title(key)}</span><strong>{value.toLocaleString()}</strong><small>{admin ? 'Across the research workspace' : 'Within your authorized records'}</small><ArrowUpRight size={22} /></div>)}</div>}</Resource><SelectedModelEvaluation /><div className="section-line"><h2>{admin ? 'Recent experiments' : 'Your patient workspace'}</h2><a href={admin ? '#/federated' : '#/add-patient'} className="text-link">{admin ? 'View all experiments' : 'Add a patient'}<Plus size={16} /></a></div><Resource resource={activity}>{data => admin ? <ExperimentTable rows={data.slice(0, 5)} /> : <PatientCards rows={data.items} />}</Resource><Notice /></>
}

function SelectedModelEvaluation() {
  const resource = useResource('/model/evaluation')
  return <Resource resource={resource}>{data => <section className="card selected-model-evaluation" aria-label="Selected model evaluation"><div className="section-line"><div><span className="eyebrow">MODEL USED FOR NEW IMAGE ANALYSES</span><h2>Measured test performance</h2></div><span className="pill">RESNET18</span></div>{data.status !== 'verified' ? <p>{data.reason}</p> : <><div className="evaluation-grid"><div><span>Test accuracy</span><strong data-testid="selected-model-accuracy">{percent(data.test.accuracy)}</strong></div><div><span>Balanced accuracy</span><strong>{percent(data.test.balanced_accuracy)}</strong></div><div><span>Macro F1</span><strong>{percent(data.test.macro_f1)}</strong></div><div><span>Test images</span><strong>{data.test.sample_count}</strong></div></div><p><strong>{data.model_version}</strong> · {title(data.algorithm)} · {data.image_size}px · {data.normalization} · Best round {data.best_round}</p><p className="small">{data.secure_aggregation_enabled ? 'Secure aggregation enabled for this model' : 'Secure aggregation was not enabled for this model'} · {data.dp_enabled ? 'Experimental DP-SGD enabled' : 'DP-SGD was not enabled'}</p><Notice>{data.validation_scope}. {data.notice} This is dataset-level performance, not an individual patient’s diagnostic certainty.</Notice></>}</section>}</Resource>
}

const clinicalFields = ['smoking_history', 'family_history', 'respiratory_conditions', 'symptoms', 'medical_history', 'allergies', 'medications', 'doctor_notes']
function PatientForm({ patient, onSaved }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    const values = Object.fromEntries(new FormData(event.currentTarget)); values.follow_up_date ||= null
    try { const data = await api(patient ? `/patients/${patient.id}` : '/patients', { method: patient ? 'PATCH' : 'POST', body: values }); if (onSaved) onSaved(data); else navigate(`patient/${data.id}`) }
    catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  return <section className="card"><div className="section-line"><div><span className="eyebrow">{patient ? 'UPDATE RECORD' : 'A NEW PATIENT RECORD'}</span><h2>{patient ? 'Edit patient information' : 'Start with the person.'}</h2><p>Record only information relevant to care and this research workflow.</p></div><span className="icon-tile coral"><Users /></span></div><form onSubmit={submit}><div className="form-grid"><Field label="Full name" name="full_name" required value={patient?.full_name} maxLength={160} /><Field label="Date of birth" name="date_of_birth" type="date" required value={patient?.date_of_birth} min="1900-01-01" max={new Date().toLocaleDateString('en-CA')} /><Field label="Sex" name="sex" options={['Not specified', 'Female', 'Male', 'Other']} value={patient?.sex} required /><Field label="Contact (optional)" name="contact" value={patient?.contact} maxLength={200} /><Field label="Smoking status" name="smoking_status" options={['Unknown', 'Never', 'Former', 'Current']} value={patient?.smoking_status} /><Field label="Follow-up date" name="follow_up_date" type="date" value={patient?.follow_up_date} />{clinicalFields.map(key => <Field key={key} name={key} label={title(key)} type="textarea" value={patient?.[key]} maxLength={['doctor_notes', 'medical_history'].includes(key) ? 8000 : 4000} />)}</div><ErrorBox error={error} /><div className="form-actions"><button type="button" className="button" onClick={() => onSaved ? onSaved(null) : navigate('patients')}>Cancel</button><Submit busy={busy}>{patient ? 'Save patient record' : 'Create patient record'}</Submit></div></form></section>
}

function PatientCards({ rows }) {
  if (!rows.length) return <Empty title="Your next connection starts here" text="Add a patient to begin recording clinical history and reviewing images." action={<a className="button primary" href="#/add-patient"><Plus size={16} />Add patient</a>} />
  return <div className="patient-grid">{rows.map((patient, i) => <a className={`patient-card accent-${i % 3}`} key={patient.id} href={`#/patient/${patient.id}`}><div className="patient-card-top"><span className="avatar patient-avatar">{patient.full_name.split(' ').map(s => s[0]).slice(0, 2).join('')}</span><ArrowUpRight size={21} /></div><span className="mono">{patient.id}</span><h3>{patient.full_name}</h3><p>{patient.sex} <span>·</span> Born {patient.date_of_birth}</p><div className="patient-card-bottom"><span className="pill">{patient.smoking_status}</span><small><CalendarClock size={14} />{patient.follow_up_date || 'No follow-up set'}</small></div></a>)}</div>
}

function PatientDirectory({ mode }) {
  const [search, setSearch] = useState(''), [smoking, setSmoking] = useState(''), [sort, setSort] = useState(mode === 'followups' ? 'follow_up_date' : 'updated_at'), [page, setPage] = useState(1)
  const resource = useResource(`/patients?q=${encodeURIComponent(search)}&smoking_status=${smoking}&sort=${sort}&page=${page}&follow_up=${mode === 'followups'}`)
  return <><div className="directory-banner"><div><span className="eyebrow">YOUR AUTHORIZED RECORDS</span><h2>{mode === 'followups' ? 'Keep the next step in sight.' : mode === 'analysis' ? 'Choose a patient. Open a new perspective.' : 'People at the center.'}</h2><p>{mode === 'analysis' ? 'Open a patient, then use Medical Images or AI Analysis to upload and review a scan.' : 'Clinical history, image analyses, and follow-ups in one place.'}</p></div><a href="#/add-patient" className="button primary"><Plus size={18} />Add patient</a></div><div className="toolbar"><label className="search"><Search size={18} /><input aria-label="Search patients" placeholder="Search by name or patient ID…" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} /></label><select aria-label="Filter smoking status" value={smoking} onChange={e => { setSmoking(e.target.value); setPage(1) }}><option value="">All smoking statuses</option>{['Never', 'Former', 'Current', 'Unknown'].map(s => <option key={s}>{s}</option>)}</select><select aria-label="Sort patients" value={sort} onChange={e => { setSort(e.target.value); setPage(1) }}><option value="updated_at">Recently updated</option><option value="full_name">Name A–Z</option><option value="follow_up_date">Follow-up date</option></select></div><Resource resource={resource}>{data => <><div className="section-line"><span className="small">{data.total} patient record{data.total !== 1 ? 's' : ''}</span><span className="pill">DOCTOR ACCESS ONLY</span></div><PatientCards rows={data.items} /><div className="pagination"><button aria-label="Previous page" disabled={page === 1} onClick={() => setPage(page - 1)}><ChevronLeft size={18} /></button><span>Page {page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span><button aria-label="Next page" disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}><ChevronRight size={18} /></button></div></>}</Resource></>
}

function PatientProfile({ id }) {
  const patient = useResource(`/patients/${id}`)
  const [tab, setTab] = useState('Overview'), [editing, setEditing] = useState(false)
  return <Resource resource={patient}>{data => editing ? <PatientForm patient={data} onSaved={() => { setEditing(false); patient.reload() }} /> : <><section className="patient-banner"><div className="avatar">{data.full_name.slice(0, 2).toUpperCase()}</div><div><span className="mono">{data.id}</span><h2>{data.full_name}</h2><p>{data.sex} · Born {data.date_of_birth} · {data.smoking_status} smoker status</p></div><button className="button" onClick={() => setEditing(true)}>Edit record<ArrowUpRight size={16} /></button></section><div className="tabs" role="tablist" aria-label="Patient profile">{['Overview', 'Clinical History', 'Medical Images', 'AI Analysis', 'Visit Timeline', 'Reports'].map(name => <button role="tab" aria-selected={tab === name} key={name} className={tab === name ? 'selected' : ''} onClick={() => setTab(name)}>{name}</button>)}</div><div role="tabpanel">{tab === 'Overview' && <div className="two-column"><section className="card"><span className="eyebrow">PATIENT SNAPSHOT</span><h2>Clinical overview</h2><dl className="details">{['contact', 'symptoms', 'medical_history', 'allergies', 'medications', 'doctor_notes', 'follow_up_date'].map(key => <div key={key}><dt>{title(key)}</dt><dd>{data[key] || 'Not recorded'}</dd></div>)}</dl></section><section className="card lavender"><HeartPulse size={38} /><h2>Context before<br />classification.</h2><p>Review history and the original image before drawing a clinical conclusion.</p><button className="button primary" onClick={() => setTab('AI Analysis')}>Open image analysis<ArrowRight size={17} /></button><Notice /></section></div>}{tab === 'Clinical History' && <ClinicalHistory patient={data} />}{['Medical Images', 'AI Analysis'].includes(tab) && <AnalysisWorkspace key={`${id}-${tab}`} patient={data} />}{tab === 'Visit Timeline' && <Visits patient={data} onSave={patient.reload} />}{tab === 'Reports' && <PatientReports id={id} />}</div></>}</Resource>
}

function ClinicalHistory({ patient }) {
  const resource = useResource(`/patients/${patient.id}/history`)
  return <><section className="card"><span className="eyebrow">DOCTOR-ENTERED INFORMATION</span><h2>Clinical history</h2><dl className="details two-details">{clinicalFields.map(key => <div key={key}><dt>{title(key)}</dt><dd>{patient[key] || 'Not recorded'}</dd></div>)}</dl></section><div className="section-line"><h2>Record revisions</h2></div><Resource resource={resource}>{rows => <div className="timeline">{rows.map(row => <details className="card" key={row.id}><summary>{date(row.created_at)}</summary><dl className="details">{Object.entries(row.snapshot).map(([key, value]) => <div key={key}><dt>{title(key)}</dt><dd>{value || 'Not recorded'}</dd></div>)}</dl></details>)}</div>}</Resource></>
}

function AnalysisWorkspace({ patient }) {
  const images = useResource(`/patients/${patient.id}/images`), history = useResource(`/patients/${patient.id}/analyses`)
  const [selectedImage, setSelectedImage] = useState(null), [selectedAnalysis, setSelectedAnalysis] = useState(null), [busy, setBusy] = useState(''), [error, setError] = useState('')
  const image = selectedImage || images.data?.[0]
  const analysis = selectedAnalysis?.image_id === image?.id ? selectedAnalysis : history.data?.find(item => item.image_id === image?.id)
  async function upload(event) {
    const file = event.target.files?.[0]; if (!file) return
    setBusy('upload'); setError('')
    const body = new FormData(); body.append('image', file)
    try { const data = await api(`/patients/${patient.id}/images`, { method: 'POST', body }); setSelectedImage(data); images.reload() }
    catch (error) { setError(error.message) } finally { setBusy(''); event.target.value = '' }
  }
  async function analyze() {
    setBusy('analyze'); setError('')
    try { const data = await api(`/patients/${patient.id}/analyze`, { method: 'POST', body: { image_id: image.id } }); setSelectedAnalysis(data); setSelectedImage(image); history.reload() }
    catch (error) { setError(error.message) } finally { setBusy('') }
  }
  return <><Notice /><div className="analysis-layout"><section className="card image-workbench"><div className="section-line"><div><span className="eyebrow">01 / IMAGE WORKBENCH</span><h2>A closer look.</h2></div><span className="pill">PNG / JPEG</span></div><label className={`upload-zone ${busy ? 'disabled' : ''}`}><Upload size={24} /><strong>{busy === 'upload' ? 'Validating and protecting image…' : 'Choose a medical image'}</strong><span>PNG or JPEG · up to 10 MiB · no DICOM support</span><input type="file" aria-label="Upload medical image" accept="image/png,image/jpeg" disabled={!!busy} onChange={upload} /></label><ErrorBox error={error} /><Resource resource={images}>{rows => rows.length ? <><label className="field"><span>Stored images</span><select aria-label="Select medical image" value={image?.id || ''} onChange={e => setSelectedImage(rows.find(row => row.id === e.target.value))}>{rows.map((row, i) => <option key={row.id} value={row.id}>Image {rows.length - i} · {date(row.created_at)}</option>)}</select></label><div className="scan-view"><img src={image?.url} alt="Original uploaded medical image" /><span>ORIGINAL IMAGE</span></div><button className="button primary full" disabled={!!busy || !image} onClick={analyze}><Sparkles size={17} />{busy === 'analyze' ? 'Running ResNet18 + Grad-CAM…' : 'Run ResNet18 analysis'}</button><p className="small">Analysis is automatically saved. Images must be suitable for the trained dataset; image content is not an automated modality certification.</p></> : <Empty title="An image opens the next step" text="Upload a supported research image for this patient." />}</Resource>{analysis && <div className="heatmap"><div className="section-line"><h3>Grad-CAM perspective</h3><span className="pill">LAYER 4</span></div><img src={analysis.heatmap_url} alt="ResNet18 Grad-CAM explanatory overlay" /><p className="small">Associated model regions; not validated tumor localization.</p></div>}</section><div><Resource resource={history}>{rows => <>{rows.length > 1 && <label className="field history-select"><span>Analysis history</span><select value={analysis?.id || ''} onChange={e => { const item = rows.find(row => row.id === e.target.value); setSelectedAnalysis(item); setSelectedImage(images.data?.find(image => image.id === item.image_id)) }}><option value="" disabled>Select a saved analysis</option>{rows.map(row => <option key={row.id} value={row.id}>{date(row.created_at)} · {row.result.predicted_class}</option>)}</select></label>}{analysis ? <AnalysisResult key={analysis.id} analysis={analysis} onSave={data => { setSelectedAnalysis(data); history.reload() }} /> : <section className="card prediction-empty"><span className="icon-tile violet"><Activity /></span><h2>Evidence comes<br />after analysis.</h2><p>Your prediction summary, per-class probabilities, model metadata, and doctor review will appear here after a successful inference.</p><span className="pill">RESNET18 ONLY</span></section>}</>}</Resource></div></div></>
}

function AnalysisResult({ analysis, onSave }) {
  const [busy, setBusy] = useState(''), [message, setMessage] = useState(''), [error, setError] = useState('')
  const result = analysis.result
  async function save(event) {
    event.preventDefault(); setBusy('save'); setError(''); setMessage('')
    try { const data = await api(`/analyses/${analysis.id}`, { method: 'PATCH', body: Object.fromEntries(new FormData(event.currentTarget)) }); onSave(data); setMessage('Doctor review saved.') }
    catch (error) { setError(error.message) } finally { setBusy('') }
  }
  async function report(event) {
    const body = Object.fromEntries(new FormData(event.currentTarget.form))
    setBusy('report'); setError('')
    try { const reviewed = await api(`/analyses/${analysis.id}`, { method: 'PATCH', body }); onSave(reviewed); const data = await api(`/patients/${analysis.patient_id}/reports`, { method: 'POST', body: { analysis_id: analysis.id } }); window.location.assign(data.download_url); setMessage('Report saved to patient history.') }
    catch (error) { setError(error.message) } finally { setBusy('') }
  }
  return <><section className="card result-card"><span className="eyebrow">02 / MODEL OUTPUT</span><span className="model-badge"><Sparkles size={16} />RESNET18</span><h2>{result.predicted_class}</h2><p className="small">Research classification · {date(analysis.created_at)}</p><div className="probabilities">{Object.entries(result.probabilities).map(([name, probability]) => <div key={name}><div><span>{name}</span><strong>{percent(probability)}</strong></div><div className="prob-track"><span style={{ width: `${probability * 100}%` }} /></div></div>)}</div><dl className="details compact"><div><dt>Model version</dt><dd>{result.model_version}</dd></div><div><dt>Input</dt><dd>{result.model_metadata.preprocessing.image_size} × {result.model_metadata.preprocessing.image_size} RGB</dd></div><div><dt>Analysis latency</dt><dd>{result.inference_ms.toFixed(0)} ms including Grad-CAM</dd></div><div><dt>Validation scope</dt><dd>{result.model_metadata.validation_scope}</dd></div></dl><Notice /></section><section className="card"><span className="eyebrow">03 / DOCTOR REVIEW</span><h2>Your clinical perspective.</h2><form onSubmit={save}><Field label="Doctor observations" type="textarea" name="observations" value={analysis.observations} maxLength={8000} /><Field label="Doctor-entered follow-up recommendations" type="textarea" name="follow_up" value={analysis.follow_up} maxLength={8000} /><ErrorBox error={error} />{message && <p className="success" role="status"><Check size={16} />{message}</p>}<div className="form-actions"><Submit busy={!!busy}>Save review</Submit><button type="button" className="button" disabled={!!busy} onClick={report}><ArrowDownToLine size={16} />{busy === 'report' ? 'Creating…' : 'Generate PDF'}</button></div><p className="small">Generating a report also saves your current review and follow-up recommendations.</p></form></section></>
}

function Visits({ patient, onSave }) {
  const resource = useResource(`/patients/${patient.id}/visits`)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); const form = event.currentTarget
    const body = Object.fromEntries(new FormData(form)); body.follow_up_date ||= null
    try { await api(`/patients/${patient.id}/visits`, { method: 'POST', body }); form.reset(); resource.reload(); onSave() } catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  return <div className="two-column"><section className="card"><span className="eyebrow">THE NEXT CHAPTER</span><h2>Add a visit</h2><form onSubmit={submit}><Field label="Visit notes" type="textarea" name="notes" required maxLength={8000} /><Field label="Follow-up date" type="date" name="follow_up_date" /><ErrorBox error={error} /><Submit busy={busy}>Save visit</Submit></form></section><Resource resource={resource}>{rows => rows.length ? <div className="timeline">{rows.map(row => <section className="card" key={row.id}><span className="eyebrow">{date(row.created_at)}</span><p className="preserve">{row.notes}</p><span className="pill">Follow-up: {row.follow_up_date || 'Not scheduled'}</span></section>)}</div> : <Empty title="A history in the making" text="Saved visit notes and follow-up dates will appear here." />}</Resource></div>
}

function PatientReports({ id }) {
  const resource = useResource(`/patients/${id}/reports`)
  return <Resource resource={resource}>{rows => <ReportList rows={rows} />}</Resource>
}
function ReportList({ rows }) {
  return rows.length ? <div className="record-list">{rows.map(row => <article className="card record-row" key={row.id}><span className="icon-tile coral"><FileText /></span><div><h3>Patient analysis report</h3><p>{row.patient_id} · {date(row.created_at)}</p></div><a className="button" href={row.download_url}><ArrowDownToLine size={17} />Download PDF</a></article>)}</div> : <Empty title="A report worth keeping" text="Generate a PDF from a saved AI analysis and doctor review. Your protected report snapshots will appear here." />
}
function Records({ type }) {
  const resource = useResource(type === 'reports' ? '/reports' : '/analyses')
  return <><Notice /><Resource resource={resource}>{rows => type === 'reports' ? <ReportList rows={rows} /> : rows.length ? <div className="record-list">{rows.map(row => <a href={`#/patient/${row.patient_id}`} className="card record-row" key={row.id}><img className="record-thumb" src={row.heatmap_url} alt="Grad-CAM preview" /><div><span className="eyebrow">{row.patient_id}</span><h3>{row.result.predicted_class}</h3><p>ResNet18 · {date(row.created_at)}</p></div><ArrowUpRight /></a>)}</div> : <Empty title="Each analysis adds a perspective" text="Completed image analyses for your authorized patients will appear here." />}</Resource></>
}

function DoctorProfile({ user, onSave }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
  async function submit(event) { event.preventDefault(); setBusy(true); setError(''); try { const data = await api('/auth/profile', { method: 'PATCH', body: Object.fromEntries(new FormData(event.currentTarget)) }); onSave(data); setMessage('Profile updated.') } catch (error) { setError(error.message) } finally { setBusy(false) } }
  return <section className="card narrow"><span className="eyebrow">YOUR PROFESSIONAL IDENTITY</span><h2>Doctor profile</h2><p>{user.email} · {user.role}</p><form onSubmit={submit}><Field name="name" label="Full name" value={user.name} required minLength={2} maxLength={160} />{['specialty', 'hospital', 'registration'].map(key => <Field key={key} name={key} label={title(key)} value={user.profile?.[key]} maxLength={160} />)}<ErrorBox error={error} />{message && <p className="success">{message}</p>}<Submit busy={busy} /></form></section>
}

function Doctors() {
  const resource = useResource('/admin/doctors')
  const [editing, setEditing] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function save(event) {
    event.preventDefault(); setBusy(true); setError('')
    const body = Object.fromEntries(new FormData(event.currentTarget)); if (editing?.id && !body.password) delete body.password
    try { await api(editing?.id ? `/admin/doctors/${editing.id}` : '/admin/doctors', { method: editing?.id ? 'PATCH' : 'POST', body }); setEditing(null); resource.reload() } catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  async function toggle(row) { setError(''); try { await api(`/admin/doctors/${row.id}/status`, { method: 'PATCH', body: { active: !row.active } }); resource.reload() } catch (error) { setError(error.message) } }
  return <><div className="directory-banner cyan-panel"><div><span className="eyebrow">THE PEOPLE BEHIND THE PERSPECTIVE</span><h2>Access with accountability.</h2><p>Provision Doctor accounts and control account status. Patient records remain restricted to their authorized doctor.</p></div><button className="button primary" onClick={() => { setEditing({}); setError('') }}><Plus size={18} />Add doctor</button></div><ErrorBox error={!editing ? error : ''} /><Resource resource={resource}>{rows => rows.length ? <div className="table-wrap"><table><thead><tr><th>Doctor</th><th>Hospital / Specialty</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.name}</strong><small>{row.email}</small></td><td>{row.profile?.hospital || 'Not recorded'}<small>{row.profile?.specialty}</small></td><td><Status value={row.active ? 'active' : 'disabled'} /></td><td><div className="row-actions"><button className="button compact-button" onClick={() => { setEditing(row); setError('') }}>Edit</button><button className="button compact-button" onClick={() => toggle(row)}>{row.active ? 'Deactivate' : 'Activate'}</button></div></td></tr>)}</tbody></table></div> : <Empty title="Build your research team" text="Create a Doctor account to start the patient workflow." />}</Resource>{editing && <Dialog onClose={() => setEditing(null)}><button className="close" aria-label="Close doctor form" onClick={() => setEditing(null)}><X /></button><span className="eyebrow">ACCOUNT MANAGEMENT</span><h2 id="doctor-dialog">{editing.id ? 'Edit doctor' : 'A new perspective.'}</h2><form onSubmit={save}><div className="form-grid"><Field label="Full name" name="name" required minLength={2} maxLength={160} value={editing.name} />{!editing.id && <Field label="Email" name="email" type="email" required maxLength={254} />}<Field label={editing.id ? 'New password (optional)' : 'Temporary password'} name="password" type="password" required={!editing.id} minLength={12} maxLength={128} autoComplete="new-password" />{['hospital', 'specialty', 'registration'].map(key => <Field key={key} label={title(key)} name={key} value={editing.profile?.[key]} maxLength={160} />)}</div><ErrorBox error={error} /><Submit busy={busy}>{editing.id ? 'Save doctor' : 'Create Doctor account'}</Submit></form></Dialog>}</>
}

function LineChart({ rows, field, label, color = '#7C3AED', percentage = false }) {
  if (!rows.length) return <Empty title="Waiting for measured rounds" text="The chart appears when the worker persists a completed round." />
  const values = rows.map(row => field(row.metrics || row))
  if (values.some(value => value == null)) return <Empty title="Local loss withheld for DP-SGD" text="Raw training loss is not covered by the gradient accountant and is not disclosed." />
  const max = Math.max(...values, percentage ? 1 : .01), width = 560, height = 180
  const points = values.map((value, i) => `${32 + i * (width - 55) / Math.max(values.length - 1, 1)},${height - 20 - value / max * (height - 45)}`)
  return <figure className="line-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}: ${values.map(v => percentage ? percent(v) : v.toFixed(3)).join(', ')}`}><line x1="30" y1={height - 20} x2={width - 10} y2={height - 20} stroke="#DAD6E4" />{[.25, .5, .75, 1].map(n => <line key={n} x1="30" y1={height - 20 - n * (height - 45)} x2={width - 10} y2={height - 20 - n * (height - 45)} stroke="#EAE7EF" strokeDasharray="4 5" />)}<polyline fill="none" stroke={color} strokeWidth="3" points={points.join(' ')} />{points.map((point, i) => <circle key={i} cx={point.split(',')[0]} cy={point.split(',')[1]} r="5" fill={color}><title>Round {i + 1}: {percentage ? percent(values[i]) : values[i].toFixed(4)}</title></circle>)}</svg><figcaption><span>Round 1</span><strong>{label}</strong><span>Round {rows.length}</span></figcaption></figure>
}

function ExperimentTable({ rows }) {
  if (!rows.length) return <Empty title="The next experiment is yours" text="Configure a centralized, FedAvg, or FedProx run. Training results will appear after the worker completes actual rounds." />
  return <div className="table-wrap"><table><thead><tr><th>Experiment / algorithm</th><th>Configuration</th><th>Status</th><th>Test macro F1</th><th /></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><a href={`#/experiment/${row.id}`}><strong>{row.algorithm.toUpperCase()}</strong><small className="mono">{row.id.slice(0, 16)}</small></a></td><td>{row.config.rounds} rounds · {row.config.image_size}px<small>{row.config.dp?.enabled ? 'DP-SGD / experimental' : 'DP-SGD disabled'} · {row.config.secure_aggregation ? 'SecAgg+ enabled' : 'Plaintext aggregation'}</small></td><td><Status value={row.status} /></td><td>{percent(row.results?.test?.macro_f1)}</td><td><a href={`#/experiment/${row.id}`} aria-label={`View ${row.id}`}><ArrowUpRight size={19} /></a></td></tr>)}</tbody></table></div>
}

function Federated() {
  const clients = useResource('/admin/federated/clients'), experiments = useResource('/admin/federated/experiments', 5000)
  const [show, setShow] = useState(false)
  const latest = experiments.data?.[0]
  return <><div className="lab-banner"><div><span className="eyebrow light">CONNECTED HOSPITALS / ONE RESEARCH QUESTION</span><h2>Learn together.<br /><em>Measure everything.</em></h2><p>Three-client local simulation · ResNet18 exclusively · FedAvg + FedProx</p><button className="button lime" onClick={() => setShow(!show)}><Plus size={18} />{show ? 'Close configuration' : 'Configure experiment'}</button></div><div className="network-art" aria-hidden="true"><span>A</span><div><Activity size={44} /></div><span>B</span><span>C</span></div></div>{show && <ExperimentForm onCreated={row => { experiments.reload(); navigate(`experiment/${row.id}`) }} />}<Resource resource={clients}>{rows => <div className="hospital-grid">{rows.map((row, index) => <section className={`card hospital-card accent-${index}`} key={row.id}><div className="section-line"><span className="icon-tile"><Hospital /></span><span className="mono">CLIENT 0{index + 1}</span></div><h3>{row.name}</h3><p>Local simulation client · ResNet18</p><Status value={row.status} /><p className="small">Actual sample counts and class distributions are recorded per experiment.</p></section>)}</div>}</Resource>{latest && <section className="card active-experiment"><div><span className="eyebrow">LATEST EXPERIMENT</span><h3>{latest.algorithm.toUpperCase()} <Status value={latest.status} /></h3><span className="mono">{latest.id}</span></div><a href={`#/experiment/${latest.id}`} className="button">Inspect rounds<ArrowUpRight size={16} /></a></section>}<div className="section-line"><h2>Experiment ledger</h2><span className="pill">PERSISTED RESULTS</span></div><Resource resource={experiments}>{rows => <ExperimentTable rows={rows} />}</Resource><Notice>Enable SecAgg+ to send masked updates from process-isolated hospitals. Plaintext experiments remain labelled separately. DP-SGD is an experimental, separately accounted option.</Notice></>
}

function ExperimentForm({ onCreated }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [dp, setDp] = useState(false), [secure, setSecure] = useState(false)
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    const values = Object.fromEntries(new FormData(event.currentTarget)), body = {}
    for (const [key, value] of Object.entries(values)) body[key] = ['algorithm', 'optimizer'].includes(key) ? value : Number(value)
    body.secure_aggregation = secure
    body.dp = { enabled: dp, delta: body.delta, noise_multiplier: body.noise_multiplier, max_grad_norm: body.max_grad_norm }
    delete body.delta; delete body.noise_multiplier; delete body.max_grad_norm
    try { onCreated(await api('/admin/federated/experiments', { method: 'POST', body })) } catch (error) { setError(error.message) } finally { setBusy(false) }
  }
  return <section className="card experiment-form"><span className="eyebrow">EXPERIMENT CONFIGURATION</span><h2>Set up your investigation.</h2><form onSubmit={submit}><div className="form-grid three-fields"><Field label="Training approach" name="algorithm" options={['fedavg', 'fedprox', 'centralized']} /><Field label="Rounds / centralized epochs" name="rounds" type="number" value="3" min="1" max="100" required /><Field label="Local epochs per round" name="local_epochs" type="number" value="1" min="1" max="20" required /><Field label="Input size" name="image_size" options={['224', '128', '64']} /><Field label="Batch size" name="batch_size" type="number" value="16" min="2" max="128" required /><Field label="Learning rate" name="learning_rate" type="number" value="0.001" step="any" min="0.000001" max="0.1" required /><Field label="Optimizer" name="optimizer" options={['adam', 'sgd']} /><Field label="Seed" name="seed" type="number" value="42" min="0" required /><Field label="Dirichlet alpha (non-IID)" name="alpha" type="number" value="0.5" step="any" min="0.01" required /><Field label="FedProx coefficient μ" name="mu" type="number" value="0.01" step="0.001" min="0" max="10" required /></div><label className="check-row"><input type="checkbox" checked={secure} onChange={e => setSecure(e.target.checked)} /><span>Enable secure aggregation (Flower SecAgg+ / three hospital processes)</span></label><label className="check-row"><input type="checkbox" checked={dp} onChange={e => setDp(e.target.checked)} /><span>Enable experimental example-level DP-SGD (Opacus / GroupNorm ResNet18)</span></label>{dp && <div className="form-grid three-fields"><Field label="Noise multiplier" name="noise_multiplier" type="number" value="1.1" min="0.1" max="20" step="0.1" required /><Field label="Maximum gradient norm" name="max_grad_norm" type="number" value="1" min="0.01" max="100" step="any" required /><Field label="Delta" name="delta" type="number" value="0.00001" min="0.00000001" max="0.009" step="any" required /></div>}<Notice>SecAgg+ supports FedAvg and FedProx, uses GroupNorm ResNet18 and requires three hospitals for key exchange, with at least two contributors. It tolerates one later dropout. Local losses and class distributions are withheld. DP budgets appear only after accountant steps. The training worker must be running.</Notice><ErrorBox error={error} /><Submit busy={busy}>Queue experiment</Submit></form></section>
}

function ExperimentDetail({ id }) {
  const experiment = useResource(`/admin/federated/experiments/${id}`, 5000), rounds = useResource(`/admin/federated/experiments/${id}/rounds`, 5000)
  return <Resource resource={experiment}>{row => <><div className="experiment-header card"><div><span className="eyebrow">{row.id}</span><h2>{row.algorithm.toUpperCase()} / ResNet18</h2><p>{row.config.image_size}px · seed {row.config.seed} · {row.config.rounds} configured rounds · {row.config.optimizer} · {row.config.secure_aggregation ? 'SecAgg+ enabled / GroupNorm' : 'Secure aggregation disabled'}</p></div><Status value={row.status} /></div><ErrorBox error={row.error} /><Resource resource={rounds}>{metrics => <><div className="metric-grid"><div className="metric-card color-0"><span>Completed rounds</span><strong>{metrics.length}<small> / {row.config.rounds}</small></strong></div><div className="metric-card color-1"><span>Latest validation accuracy</span><strong>{percent(metrics.at(-1)?.metrics.validation.accuracy)}</strong></div><div className="metric-card color-2"><span>Communication payload</span><strong>{(metrics.reduce((sum, item) => sum + item.metrics.communication_bytes, 0) / 1024 ** 2).toFixed(1)}<small> MiB</small></strong></div><div className="metric-card color-3"><span>Latest macro F1</span><strong>{percent(metrics.at(-1)?.metrics.validation.macro_f1)}</strong></div></div><div className="two-column"><section className="card"><h3>Local training loss</h3><LineChart rows={metrics} field={m => m.local_loss} label="Sample-weighted local loss" /></section><section className="card"><h3>Validation accuracy</h3><LineChart rows={metrics} field={m => m.validation.accuracy} label="Held-out validation" percentage color="#0891B2" /></section></div>{metrics.at(-1) && <section className="card"><h2>Client evidence</h2><div className="table-wrap"><table><thead><tr><th>Client</th><th>Training samples</th><th>Class distribution</th><th>Latest loss</th><th>Accountant ε / δ</th></tr></thead><tbody>{Object.entries(metrics.at(-1).metrics.distributions).map(([name, info]) => { const local = metrics.at(-1).metrics.clients[name]; return <tr key={name}><td>{name}</td><td>{info.sample_count}</td><td>{info.class_distribution_withheld && <small>Withheld (privacy)</small>}{Object.entries(info.classes).map(([label, n]) => <small key={label}>{label}: {n}</small>)}</td><td>{local.loss == null ? "Withheld (privacy)" : local.loss.toFixed(4)}</td><td>{local.privacy ? `${local.privacy.epsilon.toFixed(3)} / ${local.privacy.delta}` : 'Not enabled'}</td></tr> })}</tbody></table></div></section>}</>}</Resource><Resource resource={rounds}>{items => <SecureRoundLedger rounds={items.filter(item => item.metrics.secure_aggregation?.status === 'completed').map(item => ({ ...item, experiment_id: row.id, evidence: item.metrics.secure_aggregation }))} />}</Resource>{row.results && <Evaluation result={row.results} />}<section className="card"><h3>Recorded configuration</h3><pre>{JSON.stringify(row.config, null, 2)}</pre></section></>}</Resource>
}

function Evaluation({ result }) {
  const metrics = result.test
  return <section className="card"><span className="eyebrow">FINAL HELD-OUT TEST / VALIDATION-SELECTED CHECKPOINT</span><h2>Results with context.</h2><Notice>{result.validation_scope}. A new patient-independent external dataset is needed for stronger validation.</Notice><div className="evaluation-grid">{['accuracy', 'balanced_accuracy', 'macro_precision', 'macro_recall', 'macro_f1', 'roc_auc'].map(key => <div key={key}><span>{title(key)}</span><strong>{percent(metrics[key])}</strong></div>)}</div><div className="two-column"><div><h3>Confusion matrix</h3><div className="table-wrap"><table className="matrix"><thead><tr><th>Actual ↓ / Predicted →</th>{result.classes.map((name, i) => <th key={name} title={name}>{i + 1}</th>)}</tr></thead><tbody>{metrics.confusion_matrix.map((row, i) => <tr key={i}><th>{i + 1}. {result.classes[i]}</th>{row.map((n, j) => <td key={j} className={i === j ? 'diagonal' : ''}>{n}</td>)}</tr>)}</tbody></table></div></div><div><h3>Per-class performance</h3><div className="table-wrap"><table><thead><tr><th>Class</th><th>Sensitivity</th><th>Specificity</th></tr></thead><tbody>{Object.entries(metrics.per_class).map(([name, values]) => <tr key={name}><td>{name}</td><td>{percent(values.sensitivity)}</td><td>{percent(values.specificity)}</td></tr>)}</tbody></table></div></div></div><p className="small">{metrics.sample_count} test images · {result.training_seconds.toFixed(1)} s training · {metrics.inference_ms_per_image.toFixed(2)} ms/image including data loading · {(result.communication_bytes / 1024 ** 2).toFixed(1)} MiB · {result.communication_scope || 'logical model tensor payload (protocol overhead excluded)' }.</p></section>
}

function Comparison() {
  const resource = useResource('/admin/federated/comparison'), [cohort, setCohort] = useState('')
  return <Resource resource={resource}>{rows => {
    const key = row => `${row.results.manifest_sha256} / ${row.results.image_size}px`
    const cohorts = [...new Set(rows.map(key))], selected = cohort || cohorts[0], visible = rows.filter(row => key(row) === selected)
    return <><div className="directory-banner"><div><span className="eyebrow">LET THE EVIDENCE LEAD</span><h2>Different approaches.<br />One evaluation boundary.</h2><p>Only completed measured runs are shown. Compare within the same manifest and image size; configurations and training budgets may differ.</p></div><BarChart3 size={62} /></div>{rows.length ? <><label className="field"><span>Evaluation cohort</span><select value={selected} onChange={e => setCohort(e.target.value)}>{cohorts.map(key => <option key={key}>{key}</option>)}</select></label><section className="card"><h2>Test macro F1</h2><div className="comparison-bars">{visible.map((row, index) => <div key={row.id}><div><a href={`#/experiment/${row.id}`}><strong>{row.algorithm.toUpperCase()}{row.config.dp?.enabled ? ' + DP-SGD' : ''}{row.config.secure_aggregation ? ' + SecAgg+' : ''}</strong><small>{row.id.slice(0, 16)} · {row.config.rounds} rounds</small></a><strong>{percent(row.results.test.macro_f1)}</strong></div><div className="comparison-track"><span className={`bar-${index % 3}`} style={{ width: `${row.results.test.macro_f1 * 100}%` }} /></div></div>)}</div></section><div className="table-wrap"><table><thead><tr><th>Approach</th><th>Accuracy</th><th>Balanced accuracy</th><th>Macro precision</th><th>Macro recall</th><th>Macro F1</th><th>Training</th><th>Communication</th></tr></thead><tbody>{visible.map(row => <tr key={row.id}><td><a href={`#/experiment/${row.id}`}>{row.algorithm.toUpperCase()}{row.config.dp?.enabled ? ' + DP' : ''}{row.config.secure_aggregation ? ' + SecAgg+' : ''}</a></td>{['accuracy', 'balanced_accuracy', 'macro_precision', 'macro_recall', 'macro_f1'].map(k => <td key={k}>{percent(row.results.test[k])}</td>)}<td>{row.results.training_seconds.toFixed(1)} s</td><td>{(row.results.communication_bytes / 1024 ** 2).toFixed(1)} MiB</td></tr>)}</tbody></table></div><Notice>{visible[0]?.results.validation_scope}. Federated learning is not assumed to outperform centralized training.</Notice></> : <Empty title="A comparison needs evidence" text="Complete centralized, FedAvg, and FedProx runs using the same manifest. The worker saves actual evaluation metrics here." />}</>
  }}</Resource>
}

function SecureRoundLedger({ rounds }) {
  return <section className="card"><div className="section-line"><h2>Secure aggregation evidence</h2><span className="pill">ACTUAL PROTOCOL ROUNDS</span></div>{rounds.length ? <div className="table-wrap"><table><thead><tr><th>Experiment / round</th><th>Contributors</th><th>Threshold</th><th>Protocol messages</th><th>Stages</th></tr></thead><tbody>{rounds.map(row => <tr key={`${row.experiment_id}-${row.round_number}`}><td><a href={`#/experiment/${row.experiment_id}`}>{row.experiment_id.slice(0, 18)}</a><small>Round {row.round_number}</small></td><td>{row.evidence.contributors.length} / {row.evidence.selected_clients}</td><td>{row.evidence.reconstruction_threshold}</td><td>{((row.evidence.bytes_sent + row.evidence.bytes_received) / 1024 ** 2).toFixed(2)} MiB</td><td>{row.evidence.stages.map(stage => <small key={stage.stage}>{title(stage.stage)}: {stage.responders.length} replies</small>)}</td></tr>)}</tbody></table></div> : <Empty title="No completed secure rounds yet" text="Enable secure aggregation in a FedAvg or FedProx experiment. Existing plaintext experiments do not acquire secure aggregation protection retroactively." />}</section>
}

function Privacy() {
  const resource = useResource('/admin/federated/privacy')
  return <Resource resource={resource}>{data => <><div className="privacy-hero"><ShieldCheck size={48} /><div><span className="eyebrow">TRANSPARENCY IS PART OF THE PROTOCOL</span><h2>Privacy is a property<br />we must verify.</h2><p>Federated learning alone is not a formal privacy guarantee.</p></div></div><div className="two-column"><section className="card"><span className="pill">{data.capabilities.secure_aggregation.status.toUpperCase()}</span><h2>Secure aggregation</h2><p><strong>{data.capabilities.secure_aggregation.protocol}</strong></p><p>{data.capabilities.secure_aggregation.reason}</p><p>{data.capabilities.secure_aggregation.dropout}</p><p>{data.capabilities.secure_aggregation.scope}</p><p>{data.capabilities.secure_aggregation.limitations}</p></section><section className="card lavender"><span className="pill">{data.capabilities.differential_privacy.status.toUpperCase()}</span><h2>DP-SGD / Opacus</h2><p>{data.capabilities.differential_privacy.scope}</p><p>{data.capabilities.differential_privacy.limitations}</p><p>ResNet18 uses GroupNorm and non-inplace residual operations for compatible per-sample gradients.</p></section></div><SecureRoundLedger rounds={data.secure_rounds || []} /><div className="section-line"><h2>Accountant ledger</h2><span className="pill">ACTUAL TRAINING STEPS ONLY</span></div>{data.metrics.length ? <div className="table-wrap"><table><thead><tr><th>Experiment / client</th><th>Round</th><th>ε</th><th>δ</th><th>Noise / clip</th><th>Sample rate</th><th>Cumulative steps</th></tr></thead><tbody>{data.metrics.map(row => <tr key={row.id}><td><a href={`#/experiment/${row.experiment_id}`}>{row.experiment_id.slice(0, 12)}</a><small>{row.client}</small></td><td>{row.round_number}</td><td>{row.metrics.epsilon.toFixed(3)}</td><td>{row.metrics.delta}</td><td>{row.metrics.noise_multiplier.toFixed(3)} / {row.metrics.max_grad_norm}</td><td>{row.metrics.sample_rate.toFixed(4)}</td><td>{row.metrics.cumulative_steps}</td></tr>)}</tbody></table></div> : <Empty title="No privacy budget has been spent here" text="Enable DP-SGD for an experiment. Epsilon and delta appear only after actual Opacus accountant steps." />}</>}</Resource>
}

function Audit() {
  const [page, setPage] = useState(1), resource = useResource(`/admin/audit?page=${page}`)
  return <><Notice>Patient resource identifiers are redacted in this Admin view. Clinical records and images require doctor authorization.</Notice><Resource resource={resource}>{rows => <><div className="table-wrap"><table><thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Resource</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{date(row.created_at)}</td><td><span className="pill">{row.action}</span></td><td className="mono">{row.actor_id?.slice(0, 12) || 'Unauthenticated'}</td><td className="mono">{row.resource || '—'}</td></tr>)}</tbody></table></div><div className="pagination"><button disabled={page === 1} onClick={() => setPage(page - 1)}><ChevronLeft /></button><span>Page {page}</span><button disabled={rows.length < 50} onClick={() => setPage(page + 1)}><ChevronRight /></button></div></>}</Resource></>
}

function Settings() {
  const resource = useResource('/admin/system')
  return <Resource resource={resource}>{data => <><div className="two-column"><section className="card"><span className="eyebrow">SYSTEM STATUS</span><h2>Configured for research.</h2><dl className="details"><div><dt>Database</dt><dd>{data.database}</dd></div><div><dt>Classifier</dt><dd>ResNet18 only</dd></div><div><dt>Allowed roles</dt><dd>{data.roles.join(' / ')}</dd></div><div><dt>Upload limit</dt><dd>{data.settings.upload_max_mib} MiB · PNG / JPEG</dd></div><div><dt>Secure cookie</dt><dd>{data.settings.cookie_secure}</dd></div><div><dt>Training worker</dt><dd>{data.worker}</dd></div></dl><p className="small">Server configuration is managed through environment variables. HTTPS and Secure cookies are required for a hosted deployment.</p></section><section className="card lavender"><span className="eyebrow">INFERENCE CHECKPOINT</span><h2>Model readiness</h2><Status value={data.model.status} />{data.model.error && <ErrorBox error={data.model.error} />}{data.model.metadata && <dl className="details"><div><dt>Version</dt><dd>{data.model.metadata.version}</dd></div><div><dt>Verified class order</dt><dd>{data.model.metadata.classes.join(' / ')}</dd></div><div><dt>Input size</dt><dd>{data.model.metadata.preprocessing.image_size}px</dd></div><div><dt>Validation</dt><dd>{data.model.metadata.validation_scope}</dd></div><div><dt>SHA-256</dt><dd className="mono break">{data.model.sha256}</dd></div></dl>}</section></div><Notice /></>}</Resource>
}

