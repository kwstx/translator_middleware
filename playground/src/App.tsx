import { useEffect, useMemo, useState } from 'react'
import { DiffEditor, Editor } from '@monaco-editor/react'
import axios from 'axios'
import './App.css'

type PlaygroundState = {
  sourceProtocol: string
  targetProtocol: string
  inputText: string
}

type TranslateMeta = {
  status: string
  message: string
  latencyMs: number
}

type MappingSuggestion = {
  source_field: string
  suggestion?: string | null
  confidence?: number | null
  applied?: boolean
}

const PROTOCOLS = ['A2A', 'MCP', 'ACP']
const DEFAULT_INPUT = `{
  "intent": "schedule_meeting",
  "participants": ["alice@example.com", "bob@example.com"],
  "window": {
    "start": "2026-03-12T09:00:00Z",
    "end": "2026-03-12T11:00:00Z"
  },
  "timezone": "UTC",
  "user_id": "user_42"
}`

const DEFAULT_API_BASE =
  import.meta.env.VITE_PLAYGROUND_API_BASE ?? 'http://localhost:8000'
const DEFAULT_ENDPOINT =
  import.meta.env.VITE_PLAYGROUND_ENDPOINT ?? '/api/v1/beta/playground/translate'

const encodeState = (state: PlaygroundState) => {
  const json = JSON.stringify(state)
  return btoa(encodeURIComponent(json))
}

const decodeState = (encoded: string): PlaygroundState | null => {
  try {
    const json = decodeURIComponent(atob(encoded))
    const parsed = JSON.parse(json)
    if (
      typeof parsed?.sourceProtocol === 'string' &&
      typeof parsed?.targetProtocol === 'string' &&
      typeof parsed?.inputText === 'string'
    ) {
      return parsed
    }
    return null
  } catch {
    return null
  }
}

const safeParseJson = (text: string) => {
  try {
    return { value: JSON.parse(text), error: null }
  } catch (error) {
    return {
      value: null,
      error: error instanceof Error ? error.message : 'Invalid JSON',
    }
  }
}

const formatJson = (text: string) => {
  const parsed = safeParseJson(text)
  if (parsed.value) {
    return JSON.stringify(parsed.value, null, 2)
  }
  return text
}

const collectDiffPaths = (
  left: unknown,
  right: unknown,
  prefix = ''
): string[] => {
  if (left === right) {
    return []
  }

  if (
    typeof left !== 'object' ||
    left === null ||
    typeof right !== 'object' ||
    right === null
  ) {
    return [prefix || '(root)']
  }

  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right)) {
      return [prefix || '(root)']
    }
    const max = Math.max(left.length, right.length)
    const paths: string[] = []
    for (let i = 0; i < max; i += 1) {
      paths.push(...collectDiffPaths(left[i], right[i], `${prefix}[${i}]`))
    }
    return paths
  }

  const leftObj = left as Record<string, unknown>
  const rightObj = right as Record<string, unknown>
  const keys = new Set([...Object.keys(leftObj), ...Object.keys(rightObj)])
  const paths: string[] = []
  keys.forEach((key) => {
    const nextPrefix = prefix ? `${prefix}.${key}` : key
    if (!(key in leftObj)) {
      paths.push(`${nextPrefix} (added)`)
      return
    }
    if (!(key in rightObj)) {
      paths.push(`${nextPrefix} (removed)`)
      return
    }
    paths.push(...collectDiffPaths(leftObj[key], rightObj[key], nextPrefix))
  })
  return paths
}

function App() {
  const [sourceProtocol, setSourceProtocol] = useState(PROTOCOLS[0])
  const [targetProtocol, setTargetProtocol] = useState(PROTOCOLS[1])
  const [inputText, setInputText] = useState(DEFAULT_INPUT)
  const [outputText, setOutputText] = useState('')
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE)
  const [jwtToken, setJwtToken] = useState('')
  const [activeTab, setActiveTab] = useState<'json' | 'diff'>('json')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [translateMeta, setTranslateMeta] = useState<TranslateMeta | null>(null)
  const [mappingSuggestions, setMappingSuggestions] = useState<MappingSuggestion[]>([])
  const [isTranslating, setIsTranslating] = useState(false)
  const [shareStatus, setShareStatus] = useState<string | null>(null)

  useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const encoded = hashParams.get('state')
    if (!encoded) {
      return
    }
    const decoded = decodeState(encoded)
    if (decoded) {
      setSourceProtocol(decoded.sourceProtocol)
      setTargetProtocol(decoded.targetProtocol)
      setInputText(decoded.inputText)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const encoded = encodeState({ sourceProtocol, targetProtocol, inputText })
      const params = new URLSearchParams()
      params.set('state', encoded)
      window.history.replaceState(null, '', `#${params.toString()}`)
    }, 450)

    return () => window.clearTimeout(timeout)
  }, [sourceProtocol, targetProtocol, inputText])

  const formattedInput = useMemo(() => formatJson(inputText), [inputText])

  const outputDiffPaths = useMemo(() => {
    const leftParsed = safeParseJson(formattedInput)
    const rightParsed = safeParseJson(outputText)
    if (!leftParsed.value || !rightParsed.value) {
      return []
    }
    return collectDiffPaths(leftParsed.value, rightParsed.value).slice(0, 8)
  }, [formattedInput, outputText])

  const handleTranslate = async () => {
    setErrorMessage(null)
    setTranslateMeta(null)
    setMappingSuggestions([])

    const parsed = safeParseJson(inputText)
    if (!parsed.value) {
      setErrorMessage(parsed.error ?? 'Invalid JSON payload')
      return
    }

    const payload = parsed.value

    const apiUrl = new URL(DEFAULT_ENDPOINT, apiBase).toString()

    try {
      setIsTranslating(true)
      const start = performance.now()
      const response = await axios.post(
        apiUrl,
        {
          source_protocol: sourceProtocol,
          target_protocol: targetProtocol,
          payload,
        },
        {
          headers: jwtToken ? { Authorization: `Bearer ${jwtToken}` } : {},
        }
      )
      const elapsed = Math.round(performance.now() - start)
      const data = response.data ?? {}
      const translatedPayload = data.payload ?? {}
      setOutputText(JSON.stringify(translatedPayload, null, 2))
      setTranslateMeta({
        status: data.status ?? 'success',
        message: data.message ?? 'Translation complete',
        latencyMs: elapsed,
      })
      setMappingSuggestions(data.mapping_suggestions ?? [])
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const message =
          error.response?.data?.detail ??
          error.response?.data?.message ??
          error.message
        setErrorMessage(message)
      } else {
        setErrorMessage('Unexpected error while translating')
      }
    } finally {
      setIsTranslating(false)
    }
  }

  const handleSwap = () => {
    setSourceProtocol(targetProtocol)
    setTargetProtocol(sourceProtocol)
  }

  const handleFormat = () => {
    setInputText(formatJson(inputText))
  }

  const handleLoadExample = () => {
    setInputText(DEFAULT_INPUT)
  }

  const handleCopyShare = async () => {
    const encoded = encodeState({ sourceProtocol, targetProtocol, inputText })
    const params = new URLSearchParams()
    params.set('state', encoded)
    const url = `${window.location.origin}${window.location.pathname}#${params.toString()}`
    try {
      await navigator.clipboard.writeText(url)
      setShareStatus('Link copied to clipboard')
      setTimeout(() => setShareStatus(null), 2000)
    } catch {
      setShareStatus('Copy failed. Select the URL from the address bar.')
      setTimeout(() => setShareStatus(null), 2500)
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Live Playground</span>
          <h1>Agent Translator, on demand</h1>
          <p>
            Paste a payload, pick your source and target protocols, and watch the
            middleware reshape your message in real time.
          </p>
        </div>
        <div className="hero-actions">
          <button className="primary" onClick={handleTranslate} disabled={isTranslating}>
            {isTranslating ? 'Translating…' : 'Translate'}
          </button>
          <button className="ghost" onClick={handleSwap} type="button">
            Swap protocols
          </button>
          <div className="status">
            <span className="dot" aria-hidden="true"></span>
            <span>
              {translateMeta
                ? `${translateMeta.status} • ${translateMeta.latencyMs} ms`
                : 'Ready to translate'}
            </span>
          </div>
        </div>
      </header>

      <section className="controls">
        <label className="control">
          <span>Source protocol</span>
          <select value={sourceProtocol} onChange={(event) => setSourceProtocol(event.target.value)}>
            {PROTOCOLS.map((protocol) => (
              <option key={protocol} value={protocol}>
                {protocol}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>Target protocol</span>
          <select value={targetProtocol} onChange={(event) => setTargetProtocol(event.target.value)}>
            {PROTOCOLS.map((protocol) => (
              <option key={protocol} value={protocol}>
                {protocol}
              </option>
            ))}
          </select>
        </label>
        <label className="control wide">
          <span>API base URL</span>
          <input
            value={apiBase}
            onChange={(event) => setApiBase(event.target.value)}
            placeholder="https://your-demo-instance"
          />
        </label>
        <label className="control">
          <span>JWT (optional)</span>
          <input
            value={jwtToken}
            onChange={(event) => setJwtToken(event.target.value)}
            placeholder="Sandbox token"
          />
        </label>
      </section>

      <section className="workspace">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Source payload</h2>
              <p>Paste any JSON payload from your agent or docs.</p>
            </div>
            <div className="panel-actions">
              <button className="text" onClick={handleFormat}>
                Format JSON
              </button>
              <button className="text" onClick={handleLoadExample}>
                Load example
              </button>
            </div>
          </div>
          <div className="editor-shell">
            <Editor
              height="100%"
              language="json"
              value={inputText}
              theme="vs-dark"
              onChange={(value) => setInputText(value ?? '')}
              options={{
                minimap: { enabled: false },
                fontFamily: 'IBM Plex Mono, ui-monospace, SFMono-Regular, monospace',
                fontSize: 13,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
              }}
            />
          </div>
          {errorMessage && <div className="panel-error">{errorMessage}</div>}
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Translated output</h2>
              <p>{translateMeta?.message ?? 'Trigger a translation to see the result.'}</p>
            </div>
            <div className="tab-group">
              <button
                className={activeTab === 'json' ? 'tab active' : 'tab'}
                onClick={() => setActiveTab('json')}
              >
                JSON
              </button>
              <button
                className={activeTab === 'diff' ? 'tab active' : 'tab'}
                onClick={() => setActiveTab('diff')}
              >
                Diff
              </button>
            </div>
          </div>
          <div className="editor-shell">
            {activeTab === 'json' ? (
              <Editor
                height="100%"
                language="json"
                value={outputText || '{\n  "translated": ""\n}'}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontFamily: 'IBM Plex Mono, ui-monospace, SFMono-Regular, monospace',
                  fontSize: 13,
                  readOnly: true,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            ) : (
              <DiffEditor
                height="100%"
                language="json"
                theme="vs-dark"
                original={formattedInput}
                modified={outputText || '{\n  "translated": ""\n}'}
                options={{
                  readOnly: true,
                  renderSideBySide: true,
                  minimap: { enabled: false },
                  fontFamily: 'IBM Plex Mono, ui-monospace, SFMono-Regular, monospace',
                  fontSize: 13,
                }}
              />
            )}
          </div>
          <div className="panel-meta">
            <div>
              <h3>Field changes</h3>
              {outputDiffPaths.length === 0 ? (
                <p>No differences detected yet.</p>
              ) : (
                <ul>
                  {outputDiffPaths.map((path) => (
                    <li key={path}>{path}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3>Mapping suggestions</h3>
              {mappingSuggestions.length === 0 ? (
                <p>No ML suggestions reported.</p>
              ) : (
                <ul>
                  {mappingSuggestions.map((suggestion) => (
                    <li key={suggestion.source_field}>
                      {suggestion.source_field}
                      {suggestion.suggestion ? ` > ${suggestion.suggestion}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="share">
        <div>
          <h3>Share this scenario</h3>
          <p>
            The payload and protocol choices are stored in the URL hash so teammates can
            load the same translation instantly.
          </p>
        </div>
        <div className="share-actions">
          <button className="primary" onClick={handleCopyShare}>
            Copy share link
          </button>
          {shareStatus && <span className="share-status">{shareStatus}</span>}
        </div>
      </section>
    </div>
  )
}

export default App
