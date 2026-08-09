import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import rehypeHighlight from 'rehype-highlight'

// AI output is untrusted: rehype-sanitize strips anything not in this allowlist before it
// ever reaches the DOM, so markdown never becomes an XSS vector no matter what a model emits.
const schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code || []), ['className']],
    span: [...(defaultSchema.attributes?.span || []), ['className']],
  },
}

export default function MarkdownRenderer({ content }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight, [rehypeSanitize, schema]]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
