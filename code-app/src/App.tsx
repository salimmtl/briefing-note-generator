import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { getCurrentUser, loadReference, type Reference } from './dataverse'
import type { CurrentUser } from './domain'
import { errorMessage } from './format'
import { BrandMark, IconAdd, IconBriefings, IconChart, IconMoon, IconRefresh, IconReview, IconSun } from './icons'
import { useTheme } from './theme'
import { MyBriefingsPage } from './components/MyBriefingsPage'
import { NewRequestPage } from './components/NewRequestPage'
import { OverviewPage } from './components/OverviewPage'
import { RequestDetailPage } from './components/RequestDetailPage'
import { ReviewQueuePage } from './components/ReviewQueuePage'
import { Loading } from './components/Shared'

type ListPage = 'mine' | 'new' | 'review' | 'overview'
type Page = ListPage | 'detail'

const NAV: { page: ListPage; text: string; icon: typeof IconBriefings }[] = [
  { page: 'mine', text: 'My briefings', icon: IconBriefings },
  { page: 'new', text: 'New request', icon: IconAdd },
  { page: 'review', text: 'Review queue', icon: IconReview },
  { page: 'overview', text: 'Overview', icon: IconChart },
]

const BACK_LABELS: Record<ListPage, string> = {
  mine: 'My briefings',
  new: 'My briefings',
  review: 'Review queue',
  overview: 'Overview',
}

export default function App() {
  const { theme, toggle } = useTheme()
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [reference, setReference] = useState<Reference | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [page, setPage] = useState<Page>('mine')
  const [origin, setOrigin] = useState<ListPage>('mine')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [submitWarnings, setSubmitWarnings] = useState<string[]>([])
  const [refreshToken, setRefreshToken] = useState(0)
  const [newFormKey, setNewFormKey] = useState(0)

  const boot = useCallback(async () => {
    setBootError(null)
    try {
      const [signedIn, ref] = await Promise.all([getCurrentUser(), loadReference()])
      setUser(signedIn)
      setReference(ref)
    } catch (err) {
      setBootError(errorMessage(err))
    }
  }, [])

  useEffect(() => {
    void boot()
  }, [boot])

  function navigate(next: ListPage) {
    if (next === 'new' && page !== 'new') setNewFormKey((k) => k + 1)
    setPage(next)
    setSelectedId(null)
    setSubmitWarnings([])
  }

  function openRequest(id: string, from?: ListPage) {
    setOrigin(from ?? (page === 'detail' ? origin : page))
    setSelectedId(id)
    setSubmitWarnings([])
    setPage('detail')
  }

  async function refreshAll() {
    try {
      setReference(await loadReference())
    } catch (err) {
      setBootError(errorMessage(err))
    }
    setRefreshToken((t) => t + 1)
  }

  const activeNav: ListPage = page === 'detail' ? origin : page

  let main
  if (bootError && (!user || !reference)) {
    main = (
      <section className="panel errorPanel">
        <p className="eyebrow">Dataverse</p>
        <h2>Briefing Studio could not start</h2>
        <p>{bootError}</p>
        <button className="btn primary" type="button" onClick={() => void boot()}>
          Try again
        </button>
      </section>
    )
  } else if (!user || !reference) {
    main = <Loading text="Loading Briefing Studio…" />
  } else if (page === 'detail' && selectedId) {
    main = (
      <RequestDetailPage
        key={selectedId}
        requestId={selectedId}
        refreshToken={refreshToken}
        user={user}
        reference={reference}
        back={() => navigate(origin === 'new' ? 'mine' : origin)}
        backLabel={BACK_LABELS[origin]}
        initialWarnings={submitWarnings}
      />
    )
  } else if (page === 'new') {
    main = (
      <NewRequestPage
        key={newFormKey}
        user={user}
        reference={reference}
        cancel={() => navigate('mine')}
        onSubmitted={(id, warnings) => {
          setOrigin('mine')
          setSelectedId(id)
          setSubmitWarnings(warnings)
          setPage('detail')
        }}
      />
    )
  } else if (page === 'review') {
    main = <ReviewQueuePage reference={reference} refreshToken={refreshToken} open={(id) => openRequest(id, 'review')} />
  } else if (page === 'overview') {
    main = <OverviewPage reference={reference} refreshToken={refreshToken} open={(id) => openRequest(id, 'overview')} />
  } else {
    main = (
      <MyBriefingsPage
        user={user}
        reference={reference}
        refreshToken={refreshToken}
        open={(id) => openRequest(id, 'mine')}
        newRequest={() => navigate('new')}
      />
    )
  }

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <BrandMark size={30} />
          <div className="brand__text">
            <h1>Briefing Studio</h1>
            <p>Briefing Note Generator</p>
          </div>
        </div>
        <nav aria-label="Main">
          {NAV.map(({ page: target, text, icon: Icon }) => (
            <button
              key={target}
              type="button"
              className={activeNav === target ? 'nav active' : 'nav'}
              aria-current={activeNav === target ? 'page' : undefined}
              title={text}
              onClick={() => navigate(target)}
            >
              <Icon size={18} />
              <span className="nav__text">{text}</span>
            </button>
          ))}
        </nav>
        <div className="rail__bottom">
          <button className="nav" type="button" title="Refresh now" onClick={() => void refreshAll()}>
            <IconRefresh size={18} />
            <span className="nav__text">Refresh now</span>
          </button>
          <button className="nav" type="button" title={theme === 'dark' ? 'Light theme' : 'Dark theme'} onClick={toggle}>
            {theme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            <span className="nav__text">{theme === 'dark' ? 'Light theme' : 'Dark theme'}</span>
          </button>
          <div className="signed" title={user?.upn}>
            <span className="avatar" aria-hidden="true">
              {(user?.fullName || '?')
                .split(/\s+/)
                .map((part) => part[0])
                .slice(0, 2)
                .join('')
                .toUpperCase()}
            </span>
            <span className="signed__text">
              <b>{user?.fullName ?? 'Signing in…'}</b>
              <small>{user?.upn ?? ''}</small>
            </span>
          </div>
        </div>
      </aside>
      <main>{main}</main>
    </div>
  )
}
