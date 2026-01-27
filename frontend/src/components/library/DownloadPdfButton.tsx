import { Download, Loader2, AlertCircle } from 'lucide-react'
import { Icon } from '@/components/ui/Icon'
import { useDownloadPdf } from '@/hooks/usePapers'
import { cn } from '@/lib/utils'

interface DownloadPdfButtonProps {
  bibcode: string
}

export function DownloadPdfButton({ bibcode }: DownloadPdfButtonProps) {
  const downloadPdf = useDownloadPdf()

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        downloadPdf.mutate(bibcode)
      }}
      className={cn(
        "hover:scale-110 transition-transform",
        downloadPdf.isError && "text-destructive hover:text-destructive"
      )}
      title={downloadPdf.isError ? "Download failed. Click to retry." : "Download PDF"}
      disabled={downloadPdf.isPending}
    >
      {downloadPdf.isPending ? (
        <Loader2 size={16} className="animate-spin text-muted-foreground" />
      ) : downloadPdf.isError ? (
        <Icon icon={AlertCircle} size={16} className="text-destructive" />
      ) : (
        <Icon icon={Download} size={16} className="text-muted-foreground hover:text-primary" />
      )}
    </button>
  )
}
