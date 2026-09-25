
'use client'

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react'
import {
  ArrowDownToLine,
  CalendarDays,
  CheckCircle2,
  FileSpreadsheet,
  ImagePlus,
  Loader2,
  PackageOpen,
  RefreshCw,
  Settings2,
  Trash2,
  UploadCloud,
  XCircle,
} from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5001'

type Preview = {
  total_duties: number
  airport_reporting: number
  other_duties: number
  columns: string[]
  rows: Record<string, string>[]
}

type Item = {
  number: number
  passenger: string
  duty_id: string
  customer: string
  logo: string
  row: Record<string, string>
  png_url: string
  pdf_url: string
}

type FontResponse = { fonts: string[]; custom: string[] }

function apiUrl(path: string) {
  return `${API}${path}`
}

export default function PlacardDashboard() {
  const [file, setFile] = useState<File | null>(null)
  const [dateMode, setDateMode] = useState('Today')
  const [selectedDate, setSelectedDate] = useState('')
  const [font, setFont] = useState('Times New Roman')
  const [fonts, setFonts] = useState<FontResponse>({ fonts: [], custom: [] })
  const [preview, setPreview] = useState<Preview | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [jobId, setJobId] = useState('')
  const [loading, setLoading] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [company, setCompany] = useState('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [removeBackground, setRemoveBackground] = useState(false)
  const [logoLoading, setLogoLoading] = useState(false)
  const [fontFile, setFontFile] = useState<File | null>(null)
  const [fontLoading, setFontLoading] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)

  async function loadFonts() {
    try {
      const response = await fetch(apiUrl('/api/fonts'))
      if (!response.ok) return
      const data = await response.json()
      setFonts(data)
      if (data.fonts?.length && !data.fonts.includes(font)) setFont(data.fonts[0])
    } catch {}
  }

  useEffect(() => {
    loadFonts()
  }, [])

  const fileLabel = useMemo(() => file?.name || 'Choose an Indecab Excel/CSV export', [file])

  function resetResults() {
    setPreview(null)
    setItems([])
    setJobId('')
    setMessage('')
    setError('')
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0] || null
    setFile(next)
    resetResults()
  }

  async function getPreview(event?: FormEvent) {
    event?.preventDefault()
    if (!file) {
      setError('Please choose an XLSX, XLS, or CSV file first.')
      return
    }
    setPreviewing(true)
    setError('')
    setMessage('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('date_mode', dateMode)
      form.append('selected_date', selectedDate)
      const response = await fetch(apiUrl('/api/preview'), { method: 'POST', body: form })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not analyse the file.')
      setPreview(data)
      setItems([])
      setJobId('')
      setMessage('Duty data analysed successfully.')
    } catch (e: any) {
      setError(e.message || 'Could not analyse the file.')
    } finally {
      setPreviewing(false)
    }
  }

  async function generate(event: FormEvent) {
    event.preventDefault()
    if (!file) {
      setError('Please choose an XLSX, XLS, or CSV file first.')
      return
    }
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('date_mode', dateMode)
      form.append('selected_date', selectedDate)
      form.append('font_family', font)
      const response = await fetch(apiUrl('/api/generate'), { method: 'POST', body: form })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Placard generation failed.')
      setPreview(data.preview)
      setItems(data.items || [])
      setJobId(data.job_id)
      setMessage(`${data.count} airport placard${data.count === 1 ? '' : 's'} generated successfully.`)
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    } catch (e: any) {
      setError(e.message || 'Placard generation failed.')
    } finally {
      setLoading(false)
    }
  }

  async function uploadLogo(event: FormEvent) {
    event.preventDefault()
    if (!company || !logoFile) {
      setError('Enter a company name and select a logo image.')
      return
    }
    setLogoLoading(true)
    setError('')
    setMessage('')
    try {
      const form = new FormData()
      form.append('company', company)
      form.append('logo', logoFile)
      form.append('remove_background', String(removeBackground))
      const response = await fetch(apiUrl('/api/logos'), { method: 'POST', body: form })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Logo upload failed.')
      setMessage(`${data.message} Customer mapping saved for ${data.company}.`)
      setLogoFile(null)
      setCompany('')
      const input = document.getElementById('logo-file') as HTMLInputElement | null
      if (input) input.value = ''
    } catch (e: any) {
      setError(e.message || 'Logo upload failed.')
    } finally {
      setLogoLoading(false)
    }
  }

  async function uploadFont(event: FormEvent) {
    event.preventDefault()
    if (!fontFile) {
      setError('Choose a TTF or OTF font file.')
      return
    }
    setFontLoading(true)
    setError('')
    setMessage('')
    try {
      const form = new FormData()
      form.append('font', fontFile)
      const response = await fetch(apiUrl('/api/fonts'), { method: 'POST', body: form })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Font upload failed.')
      await loadFonts()
      setFont(data.filename)
      setFontFile(null)
      const input = document.getElementById('font-file') as HTMLInputElement | null
      if (input) input.value = ''
      setMessage(data.message)
    } catch (e: any) {
      setError(e.message || 'Font upload failed.')
    } finally {
      setFontLoading(false)
    }
  }

  async function deleteFont(filename: string) {
    if (!confirm(`Remove ${filename}?`)) return
    try {
      const response = await fetch(apiUrl(`/api/fonts/${encodeURIComponent(filename)}`), { method: 'DELETE' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not remove font.')
      await loadFonts()
      if (font === filename) setFont('Times New Roman')
      setMessage(data.message)
    } catch (e: any) {
      setError(e.message || 'Could not remove font.')
    }
  }

  return (
    <main className="min-h-screen pt-24 pb-20">
      <div className="mx-auto max-w-7xl px-4 md:px-8">
        <section className="mb-10 rounded-[2rem] bg-gray-950 px-6 py-10 text-white shadow-2xl md:px-10">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-yellow-300">Operations Studio</p>
              <h1 className="text-4xl font-light tracking-tight md:text-6xl">Airport Placard Generator</h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-gray-300 md:text-base">
                Upload the Indecab export, identify airport reporting duties, match the correct customer logo,
                and create print-ready 3840 × 2400 welcome placards and PDFs.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-sm text-gray-300">
              <div className="flex items-center gap-2"><CheckCircle2 size={16} /> Python processing backend</div>
              <div className="mt-2 flex items-center gap-2"><CheckCircle2 size={16} /> Next.js gallery interface</div>
            </div>
          </div>
        </section>

        {(message || error) && (
          <div className={`mb-6 flex items-start gap-3 rounded-2xl border px-5 py-4 text-sm ${
            error ? 'border-red-200 bg-red-50 text-red-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}>
            {error ? <XCircle size={19} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={19} className="mt-0.5 shrink-0" />}
            <span>{error || message}</span>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.3fr_.7fr]">
          <section className="rounded-3xl border border-gray-200 bg-white/90 p-6 shadow-xl md:p-8">
            <div className="mb-7 flex items-center gap-3">
              <div className="rounded-2xl bg-gray-900 p-3 text-white"><FileSpreadsheet size={21} /></div>
              <div>
                <h2 className="text-2xl font-medium text-gray-900">Duty export</h2>
                <p className="text-sm text-gray-500">Airport detection uses Reporting Address only.</p>
              </div>
            </div>

            <form onSubmit={generate} className="space-y-6">
              <label className="group block cursor-pointer rounded-2xl border-2 border-dashed border-gray-300 bg-gray-50 p-6 transition hover:border-gray-700 hover:bg-white">
                <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={onFileChange} />
                <div className="flex items-center gap-4">
                  <div className="rounded-xl bg-white p-3 shadow-sm"><UploadCloud size={22} /></div>
                  <div className="min-w-0">
                    <div className="truncate font-medium text-gray-900">{fileLabel}</div>
                    <div className="mt-1 text-xs text-gray-500">XLSX, XLS or CSV · up to 40 MB</div>
                  </div>
                </div>
              </label>

              <div className="grid gap-4 md:grid-cols-3">
                <label className="block">
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">Show duties</span>
                  <select value={dateMode} onChange={e => setDateMode(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none ring-0 focus:border-gray-800">
                    <option>Today</option>
                    <option>All Dates</option>
                    <option>Select Date</option>
                  </select>
                </label>

                <label className={`block ${dateMode !== 'Select Date' ? 'opacity-40' : ''}`}>
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">Date</span>
                  <div className="relative">
                    <CalendarDays size={17} className="pointer-events-none absolute left-3 top-3.5 text-gray-400" />
                    <input type="date" disabled={dateMode !== 'Select Date'} value={selectedDate}
                      onChange={e => setSelectedDate(e.target.value)}
                      className="w-full rounded-xl border border-gray-200 bg-white py-3 pl-10 pr-4 text-sm focus:border-gray-800" />
                  </div>
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-gray-500">Placard font</span>
                  <select value={font} onChange={e => setFont(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm focus:border-gray-800">
                    {fonts.fonts.map(name => <option key={name} value={name}>{name}</option>)}
                  </select>
                </label>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <button type="button" onClick={() => getPreview()} disabled={!file || previewing}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-300 px-5 py-3 text-sm font-medium text-gray-800 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50">
                  {previewing ? <Loader2 className="animate-spin" size={17} /> : <RefreshCw size={17} />}
                  Analyse Duties
                </button>
                <button type="submit" disabled={!file || loading}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50">
                  {loading ? <Loader2 className="animate-spin" size={17} /> : <PackageOpen size={17} />}
                  Generate Airport Placards
                </button>
              </div>
            </form>

            {preview && (
              <div className="mt-8 grid grid-cols-3 gap-3">
                <Metric label="Total Duties" value={preview.total_duties} />
                <Metric label="Airport Reporting" value={preview.airport_reporting} />
                <Metric label="Other Duties" value={preview.other_duties} />
              </div>
            )}
          </section>

          <aside className="space-y-6">
            <section className="rounded-3xl border border-gray-200 bg-white/90 p-6 shadow-xl">
              <div className="mb-5 flex items-center gap-3">
                <div className="rounded-xl bg-yellow-100 p-2.5 text-gray-900"><ImagePlus size={19} /></div>
                <div>
                  <h2 className="font-medium text-gray-900">Logo manager</h2>
                  <p className="text-xs text-gray-500">Add or replace customer logos.</p>
                </div>
              </div>
              <form onSubmit={uploadLogo} className="space-y-3">
                <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Customer / company name"
                  className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-gray-800" />
                <input id="logo-file" type="file" accept="image/*" onChange={e => setLogoFile(e.target.files?.[0] || null)}
                  className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-xs" />
                <label className="flex cursor-pointer items-center gap-2 text-xs text-gray-600">
                  <input type="checkbox" checked={removeBackground} onChange={e => setRemoveBackground(e.target.checked)} />
                  Remove connected edge background
                </label>
                <button disabled={logoLoading} className="w-full rounded-xl bg-gray-900 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">
                  {logoLoading ? 'Uploading…' : 'Upload / Replace Logo'}
                </button>
              </form>
            </section>

            <section className="rounded-3xl border border-gray-200 bg-white/90 p-6 shadow-xl">
              <div className="mb-5 flex items-center gap-3">
                <div className="rounded-xl bg-gray-100 p-2.5"><Settings2 size={19} /></div>
                <div>
                  <h2 className="font-medium text-gray-900">Font manager</h2>
                  <p className="text-xs text-gray-500">Upload TTF / OTF fonts for placards.</p>
                </div>
              </div>
              <form onSubmit={uploadFont} className="space-y-3">
                <input id="font-file" type="file" accept=".ttf,.otf" onChange={e => setFontFile(e.target.files?.[0] || null)}
                  className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-xs" />
                <button disabled={fontLoading} className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm font-semibold text-gray-800 disabled:opacity-50">
                  {fontLoading ? 'Uploading…' : 'Upload Font'}
                </button>
              </form>
              {fonts.custom.length > 0 && (
                <div className="mt-5 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Custom fonts</p>
                  {fonts.custom.map(name => (
                    <div key={name} className="flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2 text-xs">
                      <span className="truncate">{name}</span>
                      <button onClick={() => deleteFont(name)} className="ml-3 rounded-lg p-1.5 text-red-500 hover:bg-red-50" title="Remove">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </aside>
        </div>

        {items.length > 0 && (
          <section className="mt-10">
            <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-400">Generated output</p>
                <h2 className="mt-1 text-3xl font-light text-gray-900">Placard Gallery</h2>
                <p className="mt-1 text-sm text-gray-500">{items.length} print-ready placards</p>
              </div>
              {jobId && (
                <a href={apiUrl(`/api/jobs/${jobId}/zip`)}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gray-900 px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800">
                  <ArrowDownToLine size={17} /> Download All PDFs
                </a>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item, index) => (
                <article key={`${item.duty_id}-${index}`} className="overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-lg">
                  <div className="bg-gray-100 p-3">
                    <img src={apiUrl(item.png_url)} alt={`Placard for ${item.passenger}`} className="aspect-[16/10] w-full rounded-2xl object-contain bg-white" />
                  </div>
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium text-gray-900">{item.passenger}</h3>
                        <p className="mt-1 text-xs text-gray-500">Duty ID: {item.duty_id}</p>
                      </div>
                      <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[10px] font-medium text-gray-600">
                        {item.logo ? 'Logo matched' : 'No logo'}
                      </span>
                    </div>
                    <p className="mt-2 truncate text-xs text-gray-500">{item.customer || 'Customer not specified'}</p>

                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <a href={apiUrl(item.pdf_url)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-gray-900 px-3 py-2.5 text-xs font-semibold text-white">
                        <ArrowDownToLine size={14} /> PDF
                      </a>
                      <a href={apiUrl(item.png_url)} target="_blank" rel="noreferrer"
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 px-3 py-2.5 text-xs font-semibold text-gray-700">
                        Preview PNG
                      </a>
                    </div>

                    <button onClick={() => setExpanded(expanded === index ? null : index)}
                      className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-gray-50 px-3 py-2.5 text-xs font-medium text-gray-600 hover:bg-gray-100">
                      {expanded === index ? 'Hide details' : 'View duty details'}
                    </button>

                    {expanded === index && (
                      <div className="mt-4 space-y-2 border-t border-gray-100 pt-4">
                        {Object.entries(item.row).map(([key, value]) => (
                          <div key={key} className="grid grid-cols-[110px_1fr] gap-3 text-xs">
                            <span className="font-medium text-gray-400">{key}</span>
                            <span className="break-words text-gray-700">{value || '—'}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl bg-gray-50 px-4 py-4">
      <div className="text-2xl font-light text-gray-900">{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">{label}</div>
    </div>
  )
}
