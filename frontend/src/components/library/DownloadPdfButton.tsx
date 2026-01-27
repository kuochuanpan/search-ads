import { Download, Loader2 } from 'lucide-react'
import { Icon } from '@/components/ui/Icon'
import { useDownloadPdf } from '@/hooks/usePapers'

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
      className="hover:scale-110 transition-transform"
      title="Download PDF"
      disabled={downloadPdf.isPending}
    >
      {downloadPdf.isPending ? (
        <Loader2 size={16} className="animate-spin text-muted-foreground" />
      ) : (
        <Icon icon={Download} size={16} className="text-muted-foreground hover:text-primary" />
      )}
    </button>
  )
}
