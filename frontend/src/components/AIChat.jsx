import { useEffect, useRef, useState } from 'react'

import { api } from '../lib/api'

const STARTERS = [
  'When can I retire?',
  'What should I buy today?',
  'How am I tracking toward my goal?',
]

export default function AIChat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Ask about retirement timing, dividend buying priorities, or monthly contribution plans grounded in your current portfolio.',
    },
  ])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function ask(nextQuestion) {
    const trimmed = nextQuestion.trim()

    if (!trimmed || loading) return

    setQuestion('')
    setError(null)
    setMessages((current) => [...current, { role: 'user', content: trimmed }])
    setLoading(true)

    try {
      const response = await api.askAI(trimmed)
      setMessages((current) => [...current, { role: 'assistant', content: response.answer }])
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : 'AI chat failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-[2rem] border border-emerald-900/10 bg-[linear-gradient(135deg,_rgba(255,255,255,0.88),_rgba(223,239,228,0.72))] p-6 shadow-[0_24px_70px_rgba(51,41,24,0.08)] backdrop-blur motion-safe:animate-[rise_0.8s_ease-out] sm:p-7">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-emerald-900/70">
            AI portfolio chat
          </p>
          <h2 className="mt-2 font-heading text-2xl tracking-[-0.04em] text-stone-950">
            Ask what your dividends can do next.
          </h2>
        </div>
        <p className="max-w-sm text-sm leading-6 text-stone-600">
          Answers use your holdings, live prices, yields, and goal progress.
        </p>
      </div>

      <div className="flex h-[28rem] flex-col overflow-hidden rounded-[1.5rem] border border-white/80 bg-stone-50/90">
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.map((message, index) => (
            <div
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              key={`${message.role}-${index}`}
            >
              <div
                className={`max-w-[85%] rounded-[1.25rem] px-4 py-3 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'bg-emerald-800 text-white'
                    : 'border border-stone-200 bg-white text-stone-700'
                }`}
              >
                {message.content}
              </div>
            </div>
          ))}
          {loading ? (
            <div className="flex justify-start">
              <div className="rounded-[1.25rem] border border-stone-200 bg-white px-4 py-3 text-sm text-stone-500">
                Thinking through your portfolio...
              </div>
            </div>
          ) : null}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-stone-200 bg-white/80 p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {STARTERS.map((starter) => (
              <button
                className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-900 transition hover:border-emerald-400 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={loading}
                key={starter}
                onClick={() => ask(starter)}
                type="button"
              >
                {starter}
              </button>
            ))}
          </div>

          {error ? (
            <p className="mb-3 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}

          <form
            className="flex flex-col gap-3 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault()
              ask(question)
            }}
          >
            <input
              className="h-12 flex-1 rounded-2xl border border-stone-200 bg-white px-4 text-base outline-none transition focus:border-emerald-700"
              disabled={loading}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about income, retirement timing, or next buys..."
              value={question}
            />
            <button
              className="inline-flex h-12 items-center justify-center rounded-2xl bg-emerald-800 px-5 font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-400"
              disabled={loading || !question.trim()}
              type="submit"
            >
              {loading ? 'Asking...' : 'Ask AI'}
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
