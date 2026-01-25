import { useState } from 'react'
import { FileText, Search, Copy, Plus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'

export function WritingPage() {
  const [latexText, setLatexText] = useState('')
  const [outputFormat, setOutputFormat] = useState<'bibtex' | 'aastex'>('bibtex')

  const handleFindCitations = async () => {
    // TODO: Implement citation finding
    console.log('Finding citations in:', latexText)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">Writing Assistant</h1>
        <p className="text-muted-foreground">
          Paste your LaTeX text to find and fill citations
        </p>
      </div>

      {/* LaTeX Input */}
      <Card className="p-6">
        <label className="block text-sm font-medium mb-2">Paste your LaTeX text:</label>
        <textarea
          value={latexText}
          onChange={(e) => setLatexText(e.target.value)}
          placeholder={`Dark matter halos \\cite{} follow NFW profiles, though some studies
\\cite{} suggest alternative models. The mass-concentration relation
\\citep{} is well established in simulations.`}
          className="w-full h-48 p-3 font-mono text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />

        <Button className="w-full mt-4" onClick={handleFindCitations} disabled={!latexText.trim()}>
          <Icon icon={Search} size={16} />
          Find Citations
        </Button>
      </Card>

      {/* Empty Citations Found */}
      <Card className="p-6">
        <h3 className="font-medium mb-4">Empty Citations Found</h3>
        <div className="text-center py-8 text-muted-foreground">
          <Icon icon={FileText} size={48} className="mx-auto mb-4 opacity-50" />
          <p>Paste LaTeX text above and click "Find Citations" to detect empty citation commands</p>
        </div>
      </Card>

      {/* Output Format */}
      <Card className="p-6">
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium">Output Format:</span>
          <div className="flex gap-2">
            <Button
              variant={outputFormat === 'bibtex' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setOutputFormat('bibtex')}
            >
              BibTeX (.bib)
            </Button>
            <Button
              variant={outputFormat === 'aastex' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setOutputFormat('aastex')}
            >
              AASTeX (bibitem)
            </Button>
          </div>
        </div>

        <label className="block text-sm font-medium mb-2">Generated Citations:</label>
        <textarea
          readOnly
          placeholder="% Selected papers will appear here - copy to your .bib file"
          className="w-full h-32 p-3 font-mono text-sm border rounded-lg bg-secondary/50 resize-none"
        />

        <div className="flex gap-2 mt-4">
          <Button variant="outline" disabled>
            <Icon icon={Copy} size={16} />
            Copy to Clipboard
          </Button>
          <Button variant="outline" disabled>
            <Icon icon={Plus} size={16} />
            Add All to Library
          </Button>
        </div>
      </Card>
    </div>
  )
}
