import { useState, useRef } from 'react'
import { Upload, Loader2, CheckCircle2, FileText, Sparkles } from 'lucide-react'
import type { PolicyUploadResponse } from '../types'

interface UploadPanelProps {
  uploading: boolean
  lastUpload: PolicyUploadResponse | null
  extractedCount: number
  onUpload: (file: File) => void
}

export default function UploadPanel({ uploading, lastUpload, extractedCount, onUpload }: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    if (inputRef.current) inputRef.current.value = ''
  }

  const isProcessing = lastUpload?.status === 'processing'
  const isDone = lastUpload?.status === 'completed'

  return (
    <section className="rounded-xl border border-slate-700/90 bg-slate-900/90 p-6 shadow-[0_24px_60px_-45px_rgba(15,23,42,1)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Source Document</h2>
          <p className="text-xs text-slate-500">Upload one noisy artifact. We extract clear requirements.</p>
        </div>
        <div className="hidden items-center gap-1 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-400 sm:inline-flex">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          PDF live, CSV/TXT soon
        </div>
      </div>

      <button
        type="button"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex w-full cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-10 outline-none transition-all duration-200 focus-visible:border-blue-500 focus-visible:ring-4 focus-visible:ring-blue-500/20 ${
          dragOver
            ? 'border-blue-500 bg-slate-800/50'
            : 'border-slate-600 bg-gradient-to-b from-slate-900/30 to-slate-900/80 hover:border-slate-500 hover:bg-slate-800/30'
        }`}
      >
        {uploading || isProcessing ? (
          <>
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="text-sm text-slate-300">
              {uploading ? `Uploading ${lastUpload?.filename ?? 'file'}...` : 'Extracting requirements...'}
            </p>
          </>
        ) : isDone ? (
          <>
            <CheckCircle2 className="h-10 w-10 text-emerald-500" />
            <p className="text-sm text-emerald-400">
              Extracted {extractedCount} requirement{extractedCount !== 1 ? 's' : ''} from{' '}
              <span className="font-medium text-white">{lastUpload?.filename}</span>
            </p>
            <p className="text-xs text-slate-500">Drop another PDF to continue</p>
          </>
        ) : (
          <>
            <Upload className="h-10 w-10 text-slate-500" />
            <p className="text-sm text-slate-300">Drop a PDF here</p>
            <p className="text-xs text-slate-500">or click to browse your files</p>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
        />
      </button>

      {lastUpload && (
        <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <FileText className="h-3.5 w-3.5" />
          <span>
            {lastUpload.filename} - {isDone ? `${extractedCount} requirements extracted` : 'processing'}
          </span>
        </div>
      )}
    </section>
  )
}
