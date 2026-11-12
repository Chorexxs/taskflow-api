import { Download, File, Trash2 } from 'lucide-react'

/**
 * One attachment row with download/delete actions (T-127).
 */
export default function AttachmentRow({ attachment, onDownload, onDelete }) {
  return (
    <div className="flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-xl">
      <div className="flex items-center gap-3">
        <File className="w-5 h-5 text-[var(--color-text-muted)]" />
        <div>
          <p className="text-sm text-[var(--color-text-primary)]">{attachment.filename}</p>
          <p className="text-xs text-[var(--color-text-muted)]">
            {(attachment.file_size / 1024).toFixed(1)} KB
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onDownload(attachment)}
          aria-label={`Download ${attachment.filename}`}
          className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
        >
          <Download className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete(attachment.id)}
          aria-label={`Delete ${attachment.filename}`}
          className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] hover:text-[var(--color-priority-high)] transition-all"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
